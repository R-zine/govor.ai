using System.Diagnostics;
using Godot;
using Govor.Contracts;

namespace Govor.Renderer;

/// <summary>Assembles validated scene recipes in memory and releases the previous node tree.</summary>
public partial class DynamicSceneDirector : Node3D
{
    private const ulong FadeDurationUs = 350_000;
    private Node3D? _activeEnvironment;
    private ulong _fadeStartedAtUs;

    public Camera3D? CaptureCamera { get; set; }
    public DirectionalLight3D? KeyLight { get; set; }
    public WorldEnvironment? WorldEnvironment { get; set; }
    public ColorRect? TransitionOverlay { get; set; }
    public FacialTeacherAvatar? Teacher { get; set; }
    public string ActiveSceneId { get; private set; } = string.Empty;
    public long LastSceneBuildUs { get; private set; }
    public int FallbackCount { get; private set; }
    public int CachedResourceCount =>
        ProceduralSceneAssetCatalog.CachedResourceCount +
        PhotographicBackdropCatalog.CachedResourceCount;
    public bool TransitionActive => _fadeStartedAtUs != 0;
    public long LastTransitionDurationUs { get; private set; }

    public override void _Process(double delta)
    {
        _ = delta;
        if (_fadeStartedAtUs == 0 || TransitionOverlay is null)
        {
            return;
        }
        ulong elapsed = Time.GetTicksUsec() - _fadeStartedAtUs;
        float alpha = 0.72f * (1.0f - Mathf.Clamp(elapsed / (float)FadeDurationUs, 0, 1));
        TransitionOverlay.Color = new Color(0.015f, 0.02f, 0.035f, alpha);
        if (elapsed >= FadeDurationUs)
        {
            LastTransitionDurationUs = checked((long)elapsed);
            _fadeStartedAtUs = 0;
            GD.Print($"GOVOR_SCENE_TRANSITION_COMPLETE:{ActiveSceneId}");
        }
    }

    public void ApplyScene(SceneSpecificationPayload specification)
    {
        specification.Validate();
        long started = Stopwatch.GetTimestamp();
        var replacement = new Node3D { Name = $"Scene-{specification.SceneId}" };
        bool usesPhotographicBackdrop =
            PhotographicBackdropCatalog.HasBackdrop(specification.EnvironmentId);
        replacement.AddChild(usesPhotographicBackdrop
            ? PhotographicBackdropCatalog.Create(specification.EnvironmentId)
            : ProceduralSceneAssetCatalog.CreateEnvironment(specification.EnvironmentId));
        int fallbacks = 0;
        if (!usesPhotographicBackdrop)
        {
            foreach (SceneObjectPayload item in specification.Objects)
            {
                bool usedFallback = false;
                Node3D node = item.Primitive is not null
                    ? ProceduralSceneAssetCatalog.CreatePrimitive(item.Primitive)
                    : ProceduralSceneAssetCatalog.Create(item.AssetId!, out usedFallback);
                node.Name = item.InstanceId;
                node.Position = new Vector3(
                    (float)item.Position.X,
                    (float)item.Position.Y,
                    (float)item.Position.Z);
                node.RotationDegrees = new Vector3(0, (float)item.YawDegrees, 0);
                node.Scale = Vector3.One * (float)item.Scale;
                replacement.AddChild(node);
                if (usedFallback)
                {
                    fallbacks++;
                }
            }
        }

        AddChild(replacement);
        Node3D? previous = _activeEnvironment;
        _activeEnvironment = replacement;
        if (previous is not null)
        {
            RemoveChild(previous);
            previous.QueueFree();
        }

        ActiveSceneId = specification.SceneId;
        FallbackCount = fallbacks;
        ConfigureAvatar(specification);
        ConfigureCamera(specification.CameraPreset);
        ConfigureLighting(specification.LightingPreset, specification.EnvironmentId);
        if (specification.Transition == "fade" && TransitionOverlay is not null)
        {
            TransitionOverlay.Color = new Color(0.015f, 0.02f, 0.035f, 0.72f);
            _fadeStartedAtUs = Time.GetTicksUsec();
        }
        else if (TransitionOverlay is not null)
        {
            TransitionOverlay.Color = new Color(0, 0, 0, 0);
            _fadeStartedAtUs = 0;
        }
        LastSceneBuildUs = (long)Math.Ceiling(Stopwatch.GetElapsedTime(started).TotalMicroseconds);
        GD.Print(
            $"GOVOR_SCENE_APPLIED:{specification.SceneId}:" +
            $"objects={(usesPhotographicBackdrop ? 0 : specification.Objects.Count)}:" +
            $"background={(usesPhotographicBackdrop ? "photo" : "procedural")}:" +
            $"build_us={LastSceneBuildUs}:" +
            $"cache={CachedResourceCount}:fallbacks={FallbackCount}");
    }

    public static SceneSpecificationPayload DefaultCafeScene()
    {
        return new SceneSpecificationPayload(
            "cafe-ordering-v1",
            "cafe",
            "counter",
            "warm",
            "fade",
            new Vector3Payload(0, 0, -0.55),
            0,
            [
                new SceneObjectPayload("counter", "cafe-counter", new Vector3Payload(0, 0, 0.75), 0, 1),
                new SceneObjectPayload("table-left", "cafe-table", new Vector3Payload(-3, 0, 0.3), 12, 1),
                new SceneObjectPayload("chair-left", "cafe-chair", new Vector3Payload(-3, 0, 1.35), 180, 1),
                new SceneObjectPayload("cup", "cafe-cup", new Vector3Payload(0.65, 1.05, 0.55), 0, 0.9),
            ]);
    }

    public static IReadOnlyList<SceneSpecificationPayload> TourScenes()
    {
        return
        [
            DefaultCafeScene(),
            new SceneSpecificationPayload(
                "supermarket-shopping-v1",
                "supermarket",
                "wide",
                "daylight",
                "fade",
                new Vector3Payload(0, 0, -0.45),
                0,
                [
                    new SceneObjectPayload("shelf-left", "market-shelf", new Vector3Payload(-3.4, 0, -0.6), 8, 1),
                    new SceneObjectPayload("shelf-right", "market-shelf", new Vector3Payload(3.4, 0, -0.6), -8, 1),
                    new SceneObjectPayload("basket", "market-basket", new Vector3Payload(-1, 0, 1.2), 12, 1),
                    new SceneObjectPayload("crate", "market-crate", new Vector3Payload(1.65, 0, 1), -10, 1),
                ]),
            new SceneSpecificationPayload(
                "airport-travel-v1",
                "airport",
                "counter",
                "terminal",
                "fade",
                new Vector3Payload(0, 0, -0.6),
                0,
                [
                    new SceneObjectPayload("check-in", "airport-counter", new Vector3Payload(0, 0, 0.85), 0, 1),
                    new SceneObjectPayload("departures", "airport-sign", new Vector3Payload(-2.6, 2.2, -1.3), 0, 0.9),
                    new SceneObjectPayload("bench", "airport-bench", new Vector3Payload(3.1, 0, 0.2), -12, 1),
                    new SceneObjectPayload("suitcase", "airport-suitcase", new Vector3Payload(-1.55, 0, 1.3), 10, 1),
                ]),
            new SceneSpecificationPayload(
                "home-conversation-v1",
                "home",
                "conversation",
                "home",
                "fade",
                new Vector3Payload(0, 0, -0.5),
                0,
                [
                    new SceneObjectPayload("sofa", "home-sofa", new Vector3Payload(-2.8, 0, -0.65), 8, 1),
                    new SceneObjectPayload("coffee-table", "home-table", new Vector3Payload(-1.35, 0, 1), 4, 1),
                    new SceneObjectPayload("lamp", "home-lamp", new Vector3Payload(3.3, 0, -0.8), 0, 1),
                    new SceneObjectPayload("books", "home-bookshelf", new Vector3Payload(3.5, 0, -1.2), -4, 1),
                ]),
        ];
    }

    private void ConfigureAvatar(SceneSpecificationPayload specification)
    {
        if (Teacher is null)
        {
            return;
        }
        Teacher.Position = new Vector3(
            (float)specification.AvatarPosition.X,
            (float)specification.AvatarPosition.Y,
            (float)specification.AvatarPosition.Z);
        Teacher.RotationDegrees = new Vector3(0, (float)specification.AvatarYawDegrees, 0);
    }

    private void ConfigureCamera(string preset)
    {
        if (CaptureCamera is null)
        {
            return;
        }
        Vector3 position = preset switch
        {
            "conversation" => new Vector3(0, 1.46f, 0.72f),
            "wide" => new Vector3(0, 1.46f, 0.92f),
            _ => new Vector3(0, 1.46f, 0.78f),
        };
        CaptureCamera.Fov = preset == "wide" ? 32.0f : 30.0f;
        CaptureCamera.LookAtFromPosition(position, new Vector3(0, 1.48f, -0.5f), Vector3.Up);
    }

    private void ConfigureLighting(string preset, string environmentId)
    {
        if (KeyLight is not null)
        {
            KeyLight.LightColor = preset switch
            {
                "warm" => new Color(1.0f, 0.78f, 0.58f),
                "home" => new Color(1.0f, 0.72f, 0.52f),
                "terminal" => new Color(0.72f, 0.84f, 1.0f),
                _ => new Color(0.9f, 0.96f, 1.0f),
            };
            KeyLight.LightEnergy = preset == "home" ? 0.72f : 0.82f;
        }
        if (WorldEnvironment?.Environment is not Godot.Environment environment)
        {
            return;
        }
        environment.BackgroundColor = environmentId switch
        {
            "cafe" => new Color(0.12f, 0.055f, 0.035f),
            "supermarket" => new Color(0.07f, 0.12f, 0.13f),
            "airport" => new Color(0.035f, 0.085f, 0.14f),
            "home" => new Color(0.11f, 0.065f, 0.05f),
            _ => new Color(0.025f, 0.04f, 0.075f),
        };
    }
}
