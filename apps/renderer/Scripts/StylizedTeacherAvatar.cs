using System.Diagnostics;
using Godot;
using Govor.Contracts;

namespace Govor.Renderer;

/// <summary>
/// Repository-owned CC0 stylized teacher with bounded state and speech animation.
/// </summary>
public partial class StylizedTeacherAvatar : Node3D
{
    private Node3D? _rig;
    private Node3D? _head;
    private Node3D? _leftArm;
    private Node3D? _rightArm;
    private MeshInstance3D? _mouth;
    private MeshInstance3D? _leftEye;
    private MeshInstance3D? _rightEye;
    private MeshInstance3D? _leftBrow;
    private MeshInstance3D? _rightBrow;
    private AvatarAnimationPayload? _speechAnimation;
    private ulong _speechStartedAtUs;
    private string _sessionAction = "session_started";
    private double _animationProcessTotalUs;
    private long _animationProcessSamples;

    public string CurrentViseme { get; private set; } = "silence";
    public float CurrentMouthOpenness { get; private set; }
    public bool IsVisuallyComplete =>
        _rig is not null && _head is not null && _mouth is not null &&
        _leftEye is not null && _rightEye is not null;
    public double AverageAnimationProcessUs =>
        _animationProcessSamples == 0 ? 0 : _animationProcessTotalUs / _animationProcessSamples;

    public override void _Ready()
    {
        BuildAvatar();
    }

    public override void _Process(double delta)
    {
        long started = Stopwatch.GetTimestamp();
        Animate(delta);
        _animationProcessTotalUs += Stopwatch.GetElapsedTime(started).TotalMicroseconds;
        _animationProcessSamples++;
    }

    public void ApplySessionAction(string action, AvatarAnimationPayload? speechAnimation = null)
    {
        _sessionAction = action;
        _speechAnimation = speechAnimation;
        _speechStartedAtUs = Time.GetTicksUsec();
        if (speechAnimation is not null)
        {
            GD.Print(
                $"GOVOR_AVATAR_SPEECH_STARTED:source={speechAnimation.VisemeSource}:" +
                $"energy={speechAnimation.SpeechEnergy.Count}:visemes={speechAnimation.Visemes.Count}:" +
                $"duration_us={speechAnimation.DurationUs}");
        }
        if (action != "teacher_speaking")
        {
            ApplyMouth("silence", 0.0f);
        }
    }

    private void BuildAvatar()
    {
        _rig = new Node3D { Name = "TeacherRig" };
        AddChild(_rig);

        StandardMaterial3D skin = Material("skin", new Color(0.78f, 0.52f, 0.37f));
        StandardMaterial3D jacket = Material("jacket", new Color(0.12f, 0.28f, 0.48f));
        StandardMaterial3D shirt = Material("shirt", new Color(0.88f, 0.77f, 0.56f));
        StandardMaterial3D trousers = Material("trousers", new Color(0.09f, 0.12f, 0.19f));
        StandardMaterial3D hair = Material("hair", new Color(0.12f, 0.07f, 0.045f));
        StandardMaterial3D eye = Material("eye", new Color(0.035f, 0.05f, 0.07f));
        StandardMaterial3D mouth = Material("mouth", new Color(0.32f, 0.055f, 0.065f));

        _rig.AddChild(Box("Torso", new Vector3(0.92f, 1.18f, 0.48f), new Vector3(0, 1.36f, 0), jacket));
        _rig.AddChild(Box("Shirt", new Vector3(0.38f, 0.72f, 0.51f), new Vector3(0, 1.42f, 0.02f), shirt));
        _rig.AddChild(Box("Hip", new Vector3(0.82f, 0.32f, 0.45f), new Vector3(0, 0.69f, 0), trousers));
        _rig.AddChild(Box("LeftLeg", new Vector3(0.32f, 0.78f, 0.36f), new Vector3(-0.23f, 0.17f, 0), trousers));
        _rig.AddChild(Box("RightLeg", new Vector3(0.32f, 0.78f, 0.36f), new Vector3(0.23f, 0.17f, 0), trousers));

        _leftArm = Limb("LeftArm", new Vector3(-0.63f, 1.38f, 0), jacket, skin);
        _rightArm = Limb("RightArm", new Vector3(0.63f, 1.38f, 0), jacket, skin);
        _rig.AddChild(_leftArm);
        _rig.AddChild(_rightArm);

        _head = new Node3D { Name = "Head", Position = new Vector3(0, 2.22f, 0) };
        _rig.AddChild(_head);
        _head.AddChild(Sphere("Face", new Vector3(0.83f, 0.93f, 0.72f), Vector3.Zero, skin));
        _head.AddChild(Sphere("Hair", new Vector3(0.88f, 0.52f, 0.76f), new Vector3(0, 0.31f, -0.04f), hair));
        _head.AddChild(Box("HairSide", new Vector3(0.88f, 0.5f, 0.58f), new Vector3(0, 0.08f, -0.12f), hair));

        _leftEye = Box("LeftEye", new Vector3(0.12f, 0.09f, 0.035f), new Vector3(-0.19f, 0.08f, 0.36f), eye);
        _rightEye = Box("RightEye", new Vector3(0.12f, 0.09f, 0.035f), new Vector3(0.19f, 0.08f, 0.36f), eye);
        _leftBrow = Box("LeftBrow", new Vector3(0.18f, 0.035f, 0.035f), new Vector3(-0.19f, 0.22f, 0.365f), hair);
        _rightBrow = Box("RightBrow", new Vector3(0.18f, 0.035f, 0.035f), new Vector3(0.19f, 0.22f, 0.365f), hair);
        _mouth = Box("Mouth", new Vector3(0.24f, 0.055f, 0.04f), new Vector3(0, -0.19f, 0.37f), mouth);
        _head.AddChild(_leftEye);
        _head.AddChild(_rightEye);
        _head.AddChild(_leftBrow);
        _head.AddChild(_rightBrow);
        _head.AddChild(_mouth);

        var badge = Box("TeacherBadge", new Vector3(0.28f, 0.18f, 0.035f), new Vector3(0.28f, 1.55f, 0.27f), shirt);
        _rig.AddChild(badge);
    }

    private void Animate(double delta)
    {
        _ = delta;
        if (_rig is null || _head is null || _leftArm is null || _rightArm is null ||
            _leftEye is null || _rightEye is null || _leftBrow is null || _rightBrow is null)
        {
            return;
        }

        double phase = Time.GetTicksMsec() / 1000.0;
        float breath = 0.018f * (float)Math.Sin(phase * 2.2);
        _rig.Position = Vector3.Up * breath;
        _rig.RotationDegrees = new Vector3(0, 1.2f * (float)Math.Sin(phase * 0.55), 0);

        float blink = phase % 4.2 is > 4.05 and < 4.16 ? 0.12f : 1.0f;
        _leftEye.Scale = new Vector3(1, blink, 1);
        _rightEye.Scale = new Vector3(1, blink, 1);

        switch (_sessionAction)
        {
            case "teacher_speaking":
                float gesture = (float)Math.Sin(phase * 4.0);
                _leftArm.RotationDegrees = new Vector3(-8 + gesture * 8, 0, -12 - gesture * 10);
                _rightArm.RotationDegrees = new Vector3(8 - gesture * 8, 0, 12 + gesture * 10);
                _head.RotationDegrees = new Vector3(gesture * 1.8f, gesture * 2.4f, 0);
                _leftBrow.RotationDegrees = new Vector3(0, 0, -5);
                _rightBrow.RotationDegrees = new Vector3(0, 0, 5);
                AnimateSpeech();
                break;
            case "recording":
            case "awaiting_learner":
                _leftArm.RotationDegrees = new Vector3(-4, 0, -5);
                _rightArm.RotationDegrees = new Vector3(4, 0, 5);
                _head.RotationDegrees = new Vector3(-2, 0, -4);
                _leftBrow.RotationDegrees = new Vector3(0, 0, 2);
                _rightBrow.RotationDegrees = new Vector3(0, 0, -2);
                ApplyMouth("silence", 0.0f);
                break;
            case "processing":
                _rightArm.RotationDegrees = new Vector3(-24, 0, 28);
                _leftArm.RotationDegrees = new Vector3(3, 0, -7);
                _head.RotationDegrees = new Vector3(0, 9, 3);
                ApplyMouth("closed", 0.12f);
                break;
            default:
                _leftArm.RotationDegrees = new Vector3(-3, 0, -7);
                _rightArm.RotationDegrees = new Vector3(3, 0, 7);
                _head.RotationDegrees = Vector3.Zero;
                _leftBrow.RotationDegrees = Vector3.Zero;
                _rightBrow.RotationDegrees = Vector3.Zero;
                ApplyMouth("silence", 0.0f);
                break;
        }
    }

    private void AnimateSpeech()
    {
        AvatarAnimationPayload? animation = _speechAnimation;
        if (animation is null)
        {
            ApplyMouth("open", 0.35f);
            return;
        }

        long mediaTimeUs = checked((long)(Time.GetTicksUsec() - _speechStartedAtUs));
        if (mediaTimeUs >= animation.DurationUs)
        {
            ApplyMouth("silence", 0.0f);
            return;
        }

        float energy = 0.0f;
        foreach (SpeechEnergySamplePayload sample in animation.SpeechEnergy)
        {
            if (sample.MediaTimeUs > mediaTimeUs)
            {
                break;
            }
            energy = sample.LevelMilli / 1000.0f;
        }

        string viseme = "open";
        foreach (VisemeCuePayload cue in animation.Visemes)
        {
            if (cue.StartUs <= mediaTimeUs && mediaTimeUs < cue.EndUs)
            {
                viseme = cue.Viseme;
                break;
            }
        }
        ApplyMouth(viseme, energy);
    }

    private void ApplyMouth(string viseme, float energy)
    {
        if (_mouth is null)
        {
            return;
        }
        CurrentViseme = viseme;
        CurrentMouthOpenness = Mathf.Clamp(energy, 0, 1);
        Vector2 shape = viseme switch
        {
            "silence" => new Vector2(0.85f, 0.18f),
            "closed" => new Vector2(1.05f, 0.24f),
            "wide" => new Vector2(1.4f, 0.45f + energy * 0.35f),
            "round" => new Vector2(0.7f, 0.8f + energy * 0.55f),
            "teeth" => new Vector2(1.2f, 0.32f + energy * 0.25f),
            _ => new Vector2(1.0f, 0.55f + energy * 0.9f),
        };
        _mouth.Scale = new Vector3(shape.X, shape.Y, 1);
    }

    private static Node3D Limb(
        string name,
        Vector3 position,
        StandardMaterial3D sleeve,
        StandardMaterial3D skin)
    {
        var limb = new Node3D { Name = name, Position = position };
        limb.AddChild(Box("Sleeve", new Vector3(0.3f, 0.78f, 0.34f), new Vector3(0, -0.23f, 0), sleeve));
        limb.AddChild(Sphere("Hand", new Vector3(0.28f, 0.3f, 0.28f), new Vector3(0, -0.69f, 0), skin));
        return limb;
    }

    private static MeshInstance3D Box(
        string name,
        Vector3 size,
        Vector3 position,
        StandardMaterial3D material)
    {
        return new MeshInstance3D
        {
            Name = name,
            Mesh = new BoxMesh { Size = size },
            Position = position,
            MaterialOverride = material,
        };
    }

    private static MeshInstance3D Sphere(
        string name,
        Vector3 scale,
        Vector3 position,
        StandardMaterial3D material)
    {
        return new MeshInstance3D
        {
            Name = name,
            Mesh = new SphereMesh { Radius = 0.5f, Height = 1.0f },
            Scale = scale,
            Position = position,
            MaterialOverride = material,
        };
    }

    private static StandardMaterial3D Material(string name, Color color)
    {
        return new StandardMaterial3D
        {
            ResourceName = name,
            AlbedoColor = color,
            Roughness = 0.72f,
        };
    }
}
