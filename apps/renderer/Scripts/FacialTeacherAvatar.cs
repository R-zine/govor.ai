using System.Diagnostics;
using Godot;
using Govor.Contracts;

namespace Govor.Renderer;

/// <summary>
/// Selectable, locally bundled CC0 teacher with a skinned mesh and speech blend shapes.
/// The renderer applies only bounded, contract-derived animation values.
/// </summary>
public partial class FacialTeacherAvatar : Node3D
{
    private static readonly string[] RequiredSpeechMorphs =
    [
        "jawOpen",
        "viseme_PP",
        "viseme_FF",
        "viseme_aa",
        "viseme_E",
        "viseme_O",
    ];

    private static readonly string[] AnimatedMouthMorphs =
    [
        "jawOpen",
        "mouthSmile",
        "mouthFrown",
        "mouthPucker",
        "mouthPress",
        "mouthStretch",
        "mouthUpperUp",
        "viseme_PP",
        "viseme_FF",
        "viseme_TH",
        "viseme_DD",
        "viseme_kk",
        "viseme_CH",
        "viseme_SS",
        "viseme_nn",
        "viseme_RR",
        "viseme_aa",
        "viseme_E",
        "viseme_I",
        "viseme_O",
        "viseme_U",
    ];

    private static readonly string[] ExpressionMorphs =
    [
        "eyeBlinkLeft",
        "eyeBlinkRight",
        "browDownLeft",
        "browDownRight",
        "browInnerUp",
        "browOuterUpLeft",
        "browOuterUpRight",
    ];

    private readonly Dictionary<string, int> _morphs = new(StringComparer.Ordinal);
    private Node3D? _rig;
    private Node3D? _model;
    private MeshInstance3D? _face;
    private AvatarAnimationPayload? _speechAnimation;
    private ulong _speechStartedAtUs;
    private string _sessionAction = "session_started";
    private double _animationProcessTotalUs;
    private long _animationProcessSamples;

    public string InitialProfileId { get; set; } = TeacherProfileCatalog.DefaultProfileId;
    public string CurrentProfileId { get; private set; } = string.Empty;
    public string CurrentViseme { get; private set; } = "silence";
    public float CurrentMouthOpenness { get; private set; }
    public int FacialBlendShapeCount => _morphs.Count;
    public bool HasRequiredSpeechMorphs => RequiredSpeechMorphs.All(_morphs.ContainsKey);
    public bool IsVisuallyComplete =>
        _rig is not null && _model is not null && _face is not null && HasRequiredSpeechMorphs;
    public double AverageAnimationProcessUs =>
        _animationProcessSamples == 0 ? 0 : _animationProcessTotalUs / _animationProcessSamples;

    public override void _Ready()
    {
        _rig = new Node3D { Name = "TeacherRig" };
        AddChild(_rig);
        SelectProfile(InitialProfileId);
    }

    public override void _Process(double delta)
    {
        long started = Stopwatch.GetTimestamp();
        Animate(delta);
        _animationProcessTotalUs += Stopwatch.GetElapsedTime(started).TotalMicroseconds;
        _animationProcessSamples++;
    }

    public void SelectProfile(string profileId)
    {
        TeacherProfileDefinition profile = TeacherProfileCatalog.Get(profileId);
        if (_rig is null)
        {
            InitialProfileId = profile.Id;
            return;
        }
        if (_model is not null && CurrentProfileId == profile.Id)
        {
            return;
        }

        PackedScene? packedScene = GD.Load<PackedScene>(profile.AssetPath);
        if (packedScene is null)
        {
            throw new FileNotFoundException($"Unable to load teacher profile {profile.Id}.");
        }

        Node3D replacement = packedScene.Instantiate<Node3D>();
        replacement.Name = $"Teacher-{profile.DisplayName}";
        _morphs.Clear();
        _face = null;
        ConfigureMeshes(replacement);
        if (_face is null || !HasRequiredSpeechMorphs)
        {
            replacement.Free();
            throw new InvalidDataException(
                $"Teacher profile {profile.Id} does not expose the required speech morphs.");
        }

        Node3D? previous = _model;
        _model = replacement;
        _rig.AddChild(replacement);
        if (previous is not null)
        {
            _rig.RemoveChild(previous);
            previous.QueueFree();
        }

        CurrentProfileId = profile.Id;
        ApplyMouth("silence", 0.0f);
        GD.Print(
            $"GOVOR_FACIAL_TEACHER_READY:profile={profile.Id}:" +
            $"blend_shapes={FacialBlendShapeCount}:speech_morphs={RequiredSpeechMorphs.Length}");
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

    private void ConfigureMeshes(Node node)
    {
        if (node is MeshInstance3D meshInstance && meshInstance.Mesh is ArrayMesh arrayMesh &&
            arrayMesh.GetBlendShapeCount() > 0)
        {
            var candidateMorphs = new Dictionary<string, int>(StringComparer.Ordinal);
            for (int index = 0; index < arrayMesh.GetBlendShapeCount(); index++)
            {
                candidateMorphs[arrayMesh.GetBlendShapeName(index).ToString()] = index;
            }
            if (RequiredSpeechMorphs.All(candidateMorphs.ContainsKey))
            {
                _face = meshInstance;
                _morphs.Clear();
                foreach ((string name, int index) in candidateMorphs)
                {
                    _morphs[name] = index;
                }
            }
        }

        foreach (Node child in node.GetChildren())
        {
            ConfigureMeshes(child);
        }
    }

    private void Animate(double delta)
    {
        _ = delta;
        if (_rig is null || _face is null)
        {
            return;
        }

        double phase = Time.GetTicksMsec() / 1000.0;
        float breath = 0.005f * (float)Math.Sin(phase * 2.15);
        _rig.Position = Vector3.Up * breath;
        _rig.RotationDegrees = new Vector3(
            0,
            0.55f * (float)Math.Sin(phase * 0.43),
            0.18f * (float)Math.Sin(phase * 0.31));

        ResetExpression();
        float blinkPhase = (float)(phase % 4.65);
        float blink = blinkPhase is > 4.48f and < 4.62f
            ? 1.0f - Math.Abs(blinkPhase - 4.55f) / 0.07f
            : 0.0f;
        SetMorph("eyeBlinkLeft", Mathf.Clamp(blink, 0, 1));
        SetMorph("eyeBlinkRight", Mathf.Clamp(blink, 0, 1));

        switch (_sessionAction)
        {
            case "teacher_speaking":
                AnimateSpeech();
                break;
            case "recording":
            case "awaiting_learner":
                ApplyMouth("silence", 0.0f);
                SetMorph("browInnerUp", 0.10f);
                break;
            case "processing":
                ApplyMouth("closed", 0.08f);
                SetMorph("browDownLeft", 0.08f);
                SetMorph("browDownRight", 0.08f);
                break;
            default:
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
        if (_face is null)
        {
            return;
        }

        CurrentViseme = viseme;
        CurrentMouthOpenness = Mathf.Clamp(energy, 0, 1);
        foreach (string morph in AnimatedMouthMorphs)
        {
            SetMorph(morph, 0.0f);
        }
        if (viseme == "silence")
        {
            SetMorph("mouthSmile", 0.035f);
            return;
        }

        float emphasis = 0.48f + CurrentMouthOpenness * 0.44f;
        switch (viseme)
        {
            case "closed":
                SetMorph("viseme_PP", emphasis);
                break;
            case "wide":
                SetMorph("viseme_aa", emphasis);
                SetMorph("jawOpen", CurrentMouthOpenness * 0.20f);
                break;
            case "round":
                SetMorph("viseme_O", emphasis);
                break;
            case "teeth":
                SetMorph("viseme_FF", emphasis);
                break;
            default:
                SetMorph("viseme_E", emphasis);
                SetMorph("jawOpen", 0.08f + CurrentMouthOpenness * 0.32f);
                break;
        }
    }

    private void ResetExpression()
    {
        foreach (string morph in ExpressionMorphs)
        {
            SetMorph(morph, 0.0f);
        }
    }

    private void SetMorph(string name, float value)
    {
        if (_face is not null && _morphs.TryGetValue(name, out int index))
        {
            _face.SetBlendShapeValue(index, Mathf.Clamp(value, 0, 1));
        }
    }
}
