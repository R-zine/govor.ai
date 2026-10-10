using Godot;

namespace Govor.Renderer;

/// <summary>
/// Builds the deliberately small Milestone 1 scene. No lesson or provider logic belongs here.
/// </summary>
public partial class MediaProofScene : Node
{
    private SubViewport? _captureViewport;
    private string? _proofImagePath;
    private ulong _runtimeStartedAtUs;
    private bool _proofImageSaved;

    public override void _Ready()
    {
        string[] arguments = OS.GetCmdlineUserArgs();
        if (arguments.Contains("--self-test", StringComparer.Ordinal))
        {
            RendererSelfTest.Run();
            GetTree().Quit();
            return;
        }

        Engine.MaxFps = RendererBridgeProtocol.TargetFrameRate;
        bool muteLocalAudio = arguments.Contains("--mute-local-audio", StringComparer.Ordinal);
        bool exitAfterTone = arguments.Contains("--exit-after-tone", StringComparer.Ordinal);
        bool noStartupTone = arguments.Contains("--no-startup-tone", StringComparer.Ordinal);
        const string controlUrlPrefix = "--control-url=";
        string? controlUrl = arguments
            .FirstOrDefault(argument => argument.StartsWith(controlUrlPrefix, StringComparison.Ordinal))?
            [controlUrlPrefix.Length..];
        const string proofImagePrefix = "--proof-image=";
        _proofImagePath = arguments
            .FirstOrDefault(argument => argument.StartsWith(proofImagePrefix, StringComparison.Ordinal))?
            [proofImagePrefix.Length..];
        _runtimeStartedAtUs = Time.GetTicksUsec();

        _captureViewport = CreateCaptureViewport();
        AddChild(_captureViewport);
        AddChild(CreateDisplay(_captureViewport));

        var videoPublisher = new SharedMemoryVideoPublisher
        {
            Name = "SharedMemoryVideoPublisher",
            SourceViewport = _captureViewport,
        };
        AddChild(videoPublisher);

        var audioPublisher = new SharedMemoryAudioPublisher
        {
            Name = "SharedMemoryAudioPublisher",
        };
        AddChild(audioPublisher);

        if (!string.IsNullOrWhiteSpace(controlUrl))
        {
            AddChild(new RendererSessionController
            {
                Name = "RendererSessionController",
                ControlUrl = controlUrl,
            });
        }

        if (!noStartupTone)
        {
            var tone = new ApplicationToneGenerator
            {
                Name = "ApplicationToneGenerator",
                PlayLocally = !muteLocalAudio,
                ExitWhenComplete = exitAfterTone,
            };
            AddChild(tone);
        }
    }

    public override void _Process(double delta)
    {
        _ = delta;
        if (_proofImageSaved || _proofImagePath is null || _captureViewport is null ||
            Time.GetTicksUsec() - _runtimeStartedAtUs < 500_000UL)
        {
            return;
        }

        Image image = _captureViewport.GetTexture().GetImage();
        try
        {
            Error result = image.SavePng(_proofImagePath);
            if (result != Error.Ok)
            {
                GD.PushError($"Unable to save renderer proof image: {result}.");
                return;
            }

            _proofImageSaved = true;
            GD.Print($"GOVOR_RENDERER_PROOF_IMAGE:{_proofImagePath}");
        }
        finally
        {
            image.Dispose();
        }
    }

    private static SubViewport CreateCaptureViewport()
    {
        var viewport = new SubViewport
        {
            Name = "CaptureViewport1280x720",
            Size = new Vector2I(
                RendererBridgeProtocol.CaptureWidth,
                RendererBridgeProtocol.CaptureHeight),
            RenderTargetUpdateMode = SubViewport.UpdateMode.Always,
            OwnWorld3D = true,
            HandleInputLocally = false,
        };

        var world = new Node3D { Name = "World" };
        viewport.AddChild(world);

        world.AddChild(new AnimatedTeacherPlaceholder
        {
            Name = "AnimatedTeacherPlaceholder",
            Position = new Vector3(0.0f, 1.25f, 0.0f),
        });

        var ground = new MeshInstance3D
        {
            Name = "Ground",
            Mesh = new PlaneMesh { Size = new Vector2(12.0f, 12.0f) },
            MaterialOverride = new StandardMaterial3D
            {
                AlbedoColor = new Color(0.11f, 0.14f, 0.19f),
                Roughness = 0.9f,
            },
        };
        world.AddChild(ground);

        var light = new DirectionalLight3D
        {
            Name = "KeyLight",
            RotationDegrees = new Vector3(-52.0f, -28.0f, 0.0f),
            LightEnergy = 1.35f,
            ShadowEnabled = true,
        };
        world.AddChild(light);

        var environment = new WorldEnvironment
        {
            Name = "Environment",
            Environment = new Godot.Environment
            {
                BackgroundMode = Godot.Environment.BGMode.Color,
                BackgroundColor = new Color(0.025f, 0.04f, 0.075f),
                AmbientLightSource = Godot.Environment.AmbientSource.Color,
                AmbientLightColor = new Color(0.3f, 0.38f, 0.5f),
                AmbientLightEnergy = 0.75f,
            },
        };
        world.AddChild(environment);

        var camera = new Camera3D
        {
            Name = "CaptureCamera",
            Current = true,
        };
        camera.LookAtFromPosition(
            new Vector3(0.0f, 2.1f, 6.0f),
            new Vector3(0.0f, 1.15f, 0.0f),
            Vector3.Up);
        world.AddChild(camera);

        return viewport;
    }

    private static TextureRect CreateDisplay(SubViewport viewport)
    {
        return new TextureRect
        {
            Name = "RendererDisplay",
            Texture = viewport.GetTexture(),
            Position = Vector2.Zero,
            Size = new Vector2(
                RendererBridgeProtocol.CaptureWidth,
                RendererBridgeProtocol.CaptureHeight),
            ExpandMode = TextureRect.ExpandModeEnum.IgnoreSize,
            StretchMode = TextureRect.StretchModeEnum.KeepAspectCentered,
        };
    }
}
