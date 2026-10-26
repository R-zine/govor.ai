using System.Globalization;
using Godot;

namespace Govor.Renderer;

/// <summary>
/// Builds the deliberately small Milestone 1 scene. No lesson or provider logic belongs here.
/// </summary>
public partial class MediaProofScene : Node
{
    private SubViewport? _captureViewport;
    private DynamicSceneDirector? _sceneDirector;
    private FacialTeacherAvatar? _teacher;
    private string? _proofImagePath;
    private string? _uiProofImagePath;
    private bool _exitAfterUiProof;
    private ulong _runtimeStartedAtUs;
    private bool _proofImageSaved;
    private bool _uiProofImageSaved;

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
        const string startupToneDelayPrefix = "--startup-tone-delay-seconds=";
        string? startupToneDelayValue = arguments
            .FirstOrDefault(argument => argument.StartsWith(
                startupToneDelayPrefix,
                StringComparison.Ordinal))?[startupToneDelayPrefix.Length..];
        double startupToneDelaySeconds = 0.0;
        if (startupToneDelayValue is not null &&
            (!double.TryParse(
                startupToneDelayValue,
                NumberStyles.Float,
                CultureInfo.InvariantCulture,
                out startupToneDelaySeconds) ||
             startupToneDelaySeconds is < 0.0 or > 300.0))
        {
            GD.PushError("The startup tone delay must be between zero and 300 seconds.");
            GetTree().Quit(2);
            return;
        }
        const string sceneTourPrefix = "--scene-tour-output=";
        string? sceneTourOutput = arguments
            .FirstOrDefault(argument => argument.StartsWith(sceneTourPrefix, StringComparison.Ordinal))?
            [sceneTourPrefix.Length..];
        bool noStartupTone = arguments.Contains("--no-startup-tone", StringComparer.Ordinal) ||
            !string.IsNullOrWhiteSpace(sceneTourOutput);
        const string controlUrlPrefix = "--control-url=";
        string? controlUrl = arguments
            .FirstOrDefault(argument => argument.StartsWith(controlUrlPrefix, StringComparison.Ordinal))?
            [controlUrlPrefix.Length..];
        const string controlCaPrefix = "--control-ca=";
        string? controlCaPath = arguments
            .FirstOrDefault(argument => argument.StartsWith(controlCaPrefix, StringComparison.Ordinal))?
            [controlCaPrefix.Length..];
        const string pairingQrPrefix = "--pairing-qr=";
        string? pairingQrPath = arguments
            .FirstOrDefault(argument => argument.StartsWith(pairingQrPrefix, StringComparison.Ordinal))?
            [pairingQrPrefix.Length..];
        const string pairingBootstrapPrefix = "--pairing-bootstrap=";
        string? pairingBootstrapPath = arguments
            .FirstOrDefault(argument => argument.StartsWith(
                pairingBootstrapPrefix,
                StringComparison.Ordinal))?[pairingBootstrapPrefix.Length..];
        const string proofImagePrefix = "--proof-image=";
        _proofImagePath = arguments
            .FirstOrDefault(argument => argument.StartsWith(proofImagePrefix, StringComparison.Ordinal))?
            [proofImagePrefix.Length..];
        const string uiProofImagePrefix = "--ui-proof-image=";
        _uiProofImagePath = arguments
            .FirstOrDefault(argument => argument.StartsWith(
                uiProofImagePrefix,
                StringComparison.Ordinal))?[uiProofImagePrefix.Length..];
        _exitAfterUiProof = arguments.Contains("--exit-after-ui-proof", StringComparer.Ordinal);
        bool showManualPairing = arguments.Contains(
            "--show-manual-pairing",
            StringComparer.Ordinal);
        _runtimeStartedAtUs = Time.GetTicksUsec();
        string selectedTeacherProfileId = TeacherProfileCatalog.LoadPreference();

        _captureViewport = CreateCaptureViewport(selectedTeacherProfileId);
        AddChild(_captureViewport);
        _sceneDirector?.ApplyScene(DynamicSceneDirector.DefaultCafeScene());
        AddChild(CreateDisplay(_captureViewport));

        HostPairingScreen? pairingScreen = null;
        if (!string.IsNullOrWhiteSpace(pairingQrPath))
        {
            pairingScreen = new HostPairingScreen
            {
                Name = "HostPairingScreen",
                QrImagePath = pairingQrPath,
                BootstrapPath = pairingBootstrapPath ?? string.Empty,
                ShowManualDetailsOnReady = showManualPairing,
                InitialTeacherProfileId = selectedTeacherProfileId,
            };
            AddChild(pairingScreen);
        }

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

        RendererSessionController? sessionController = null;
        if (!string.IsNullOrWhiteSpace(controlUrl))
        {
            sessionController = new RendererSessionController
            {
                Name = "RendererSessionController",
                ControlUrl = controlUrl,
                ControlCaPath = controlCaPath,
                PairingScreen = pairingScreen,
                SelectedTeacherProfileId = selectedTeacherProfileId,
            };
            AddChild(sessionController);
        }
        if (pairingScreen is not null)
        {
            pairingScreen.TeacherProfileSelected += profileId =>
            {
                _teacher?.SelectProfile(profileId);
                sessionController?.SelectTeacherProfile(profileId);
            };
        }

        if (!string.IsNullOrWhiteSpace(sceneTourOutput) && _sceneDirector is not null &&
            _captureViewport is not null && _teacher is not null)
        {
            AddChild(new SceneTourRunner
            {
                Name = "SceneTourRunner",
                Director = _sceneDirector,
                CaptureViewport = _captureViewport,
                Teacher = _teacher,
                OutputDirectory = sceneTourOutput,
            });
        }

        if (!noStartupTone)
        {
            var tone = new ApplicationToneGenerator
            {
                Name = "ApplicationToneGenerator",
                PlayLocally = !muteLocalAudio,
                ExitWhenComplete = exitAfterTone,
                StartDelaySeconds = startupToneDelaySeconds,
            };
            AddChild(tone);
        }
    }

    public override void _Process(double delta)
    {
        _ = delta;
        if (Time.GetTicksUsec() - _runtimeStartedAtUs < 500_000UL)
        {
            return;
        }

        if (!_proofImageSaved && _proofImagePath is not null && _captureViewport is not null)
        {
            _proofImageSaved = SaveProofImage(
                _captureViewport.GetTexture().GetImage(),
                _proofImagePath,
                "GOVOR_RENDERER_PROOF_IMAGE");
        }

        if (!_uiProofImageSaved && _uiProofImagePath is not null)
        {
            _uiProofImageSaved = SaveProofImage(
                GetViewport().GetTexture().GetImage(),
                _uiProofImagePath,
                "GOVOR_RENDERER_UI_PROOF_IMAGE");
            if (_uiProofImageSaved && _exitAfterUiProof)
            {
                GetTree().Quit();
            }
        }
    }

    private static bool SaveProofImage(Image image, string path, string marker)
    {
        try
        {
            Error result = image.SavePng(path);
            if (result != Error.Ok)
            {
                GD.PushError($"Unable to save renderer proof image: {result}.");
                return false;
            }

            GD.Print($"{marker}:{path}");
            return true;
        }
        finally
        {
            image.Dispose();
        }
    }

    private SubViewport CreateCaptureViewport(string teacherProfileId)
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

        _teacher = new FacialTeacherAvatar
        {
            Name = "FacialTeacherAvatar",
            InitialProfileId = teacherProfileId,
        };
        world.AddChild(_teacher);

        var light = new DirectionalLight3D
        {
            Name = "KeyLight",
            RotationDegrees = new Vector3(-52.0f, -28.0f, 0.0f),
            LightEnergy = 0.82f,
            ShadowEnabled = true,
        };
        world.AddChild(light);

        var faceLight = new OmniLight3D
        {
            Name = "FaceFillLight",
            Position = new Vector3(0.35f, 1.8f, 1.4f),
            LightColor = new Color(1.0f, 0.91f, 0.83f),
            LightEnergy = 0.65f,
            OmniRange = 4.5f,
            ShadowEnabled = false,
        };
        world.AddChild(faceLight);

        var environment = new WorldEnvironment
        {
            Name = "Environment",
            Environment = new Godot.Environment
            {
                BackgroundMode = Godot.Environment.BGMode.Color,
                BackgroundColor = new Color(0.025f, 0.04f, 0.075f),
                AmbientLightSource = Godot.Environment.AmbientSource.Color,
                AmbientLightColor = new Color(0.3f, 0.38f, 0.5f),
                AmbientLightEnergy = 0.45f,
            },
        };
        world.AddChild(environment);

        var camera = new Camera3D
        {
            Name = "CaptureCamera",
            Current = true,
            Fov = 30.0f,
            Near = 0.05f,
        };
        camera.LookAtFromPosition(
            new Vector3(0.0f, 1.44f, 1.2f),
            new Vector3(0.0f, 1.42f, -0.5f),
            Vector3.Up);
        world.AddChild(camera);

        var transitionLayer = new CanvasLayer { Name = "SceneTransitionLayer", Layer = 10 };
        var transitionOverlay = new ColorRect
        {
            Name = "SceneTransitionOverlay",
            Position = Vector2.Zero,
            Size = new Vector2(
                RendererBridgeProtocol.CaptureWidth,
                RendererBridgeProtocol.CaptureHeight),
            Color = new Color(0, 0, 0, 0),
            MouseFilter = Control.MouseFilterEnum.Ignore,
        };
        transitionLayer.AddChild(transitionOverlay);
        viewport.AddChild(transitionLayer);

        _sceneDirector = new DynamicSceneDirector
        {
            Name = "DynamicSceneDirector",
            CaptureCamera = camera,
            KeyLight = light,
            WorldEnvironment = environment,
            TransitionOverlay = transitionOverlay,
            Teacher = _teacher,
        };
        world.AddChild(_sceneDirector);

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
