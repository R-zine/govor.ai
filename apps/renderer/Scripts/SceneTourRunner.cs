using System.Diagnostics;
using System.Text.Json;
using Godot;
using Govor.Contracts;

namespace Govor.Renderer;

/// <summary>Bounded exported-runtime evidence for all four in-memory scene recipes.</summary>
public partial class SceneTourRunner : Node
{
    private const ulong CaptureDelayUs = 525_000;
    private readonly List<double> _frameTimesMs = [];
    private readonly List<long> _sceneBuildUs = [];
    private readonly List<long> _transitionUs = [];
    private IReadOnlyList<SceneSpecificationPayload> _scenes = [];
    private int _sceneIndex;
    private ulong _sceneAppliedAtUs;
    private ulong _memoryBeforeBytes;
    private ulong _videoMemoryBeforeBytes;
    private bool _finishing;
    private DateTime _tourStartedAtUtc;

    public required DynamicSceneDirector Director { get; init; }
    public required SubViewport CaptureViewport { get; init; }
    public required StylizedTeacherAvatar Teacher { get; init; }
    public required string OutputDirectory { get; init; }

    public override void _Ready()
    {
        Directory.CreateDirectory(OutputDirectory);
        _tourStartedAtUtc = DateTime.UtcNow;
        _scenes = DynamicSceneDirector.TourScenes();
        _memoryBeforeBytes = OS.GetStaticMemoryUsage();
        _videoMemoryBeforeBytes = RenderingServer.GetRenderingInfo(
            RenderingServer.RenderingInfo.VideoMemUsed);
        Teacher.ApplySessionAction("teacher_speaking", BenchmarkAnimation());
        ApplyCurrentScene();
    }

    public override void _Process(double delta)
    {
        _frameTimesMs.Add(delta * 1000.0);
        if (_finishing || Time.GetTicksUsec() - _sceneAppliedAtUs < CaptureDelayUs ||
            Director.TransitionActive)
        {
            return;
        }

        SaveCurrentProof();
        _transitionUs.Add(Director.LastTransitionDurationUs);
        _sceneIndex++;
        if (_sceneIndex < _scenes.Count)
        {
            ApplyCurrentScene();
            return;
        }

        _finishing = true;
        FinishTour();
    }

    private void ApplyCurrentScene()
    {
        Director.ApplyScene(_scenes[_sceneIndex]);
        _sceneBuildUs.Add(Director.LastSceneBuildUs);
        _sceneAppliedAtUs = Time.GetTicksUsec();
    }

    private void SaveCurrentProof()
    {
        SceneSpecificationPayload scene = _scenes[_sceneIndex];
        string path = Path.Combine(OutputDirectory, $"{_sceneIndex + 1}-{scene.EnvironmentId}.png");
        Image image = CaptureViewport.GetTexture().GetImage();
        try
        {
            Error result = image.SavePng(path);
            if (result != Error.Ok)
            {
                throw new IOException($"Unable to save scene proof: {result}.");
            }
        }
        finally
        {
            image.Dispose();
        }
        GD.Print($"GOVOR_SCENE_TOUR_CAPTURE:{scene.SceneId}:{path}");
    }

    private void FinishTour()
    {
        int cacheBeforeRevisit = Director.CachedResourceCount;
        ulong videoMemoryBeforeRevisit = RenderingServer.GetRenderingInfo(
            RenderingServer.RenderingInfo.VideoMemUsed);
        long started = Stopwatch.GetTimestamp();
        Director.ApplyScene(_scenes[0] with { Transition = "cut" });
        long cachedRevisitUs = (long)Math.Ceiling(Stopwatch.GetElapsedTime(started).TotalMicroseconds);
        int cacheAfterRevisit = Director.CachedResourceCount;
        ulong videoMemoryAfterRevisit = RenderingServer.GetRenderingInfo(
            RenderingServer.RenderingInfo.VideoMemUsed);

        double[] sortedFrames = _frameTimesMs.Order().ToArray();
        ulong memoryAfterBytes = OS.GetStaticMemoryUsage();
        bool staticMemoryApiAvailable = _memoryBeforeBytes > 0 && memoryAfterBytes > 0;
        var report = new
        {
            schema_version = "1.0",
            result_kind = "renderer_scene_tour",
            measured_at_utc = _tourStartedAtUtc.ToString("O"),
            measured_finished_at_utc = DateTime.UtcNow.ToString("O"),
            scenes = _scenes.Select((scene, index) => new
            {
                scene_id = scene.SceneId,
                environment_id = scene.EnvironmentId,
                object_count = scene.Objects.Count,
                build_us = _sceneBuildUs[index],
                transition_us = _transitionUs[index],
            }),
            frame_count = sortedFrames.Length,
            frame_time_ms_p50 = Percentile(sortedFrames, 0.50),
            frame_time_ms_p95 = Percentile(sortedFrames, 0.95),
            godot_static_memory_api_available = staticMemoryApiAvailable,
            godot_static_memory_before_bytes = staticMemoryApiAvailable ? _memoryBeforeBytes : (ulong?)null,
            godot_static_memory_after_bytes = staticMemoryApiAvailable ? memoryAfterBytes : (ulong?)null,
            video_memory_before_bytes = _videoMemoryBeforeBytes,
            video_memory_before_revisit_bytes = videoMemoryBeforeRevisit,
            video_memory_after_revisit_bytes = videoMemoryAfterRevisit,
            video_memory_growth_on_revisit_bytes = checked((long)videoMemoryAfterRevisit - (long)videoMemoryBeforeRevisit),
            cached_resource_count = cacheAfterRevisit,
            cached_revisit_build_us = cachedRevisitUs,
            cache_growth_on_revisit = cacheAfterRevisit - cacheBeforeRevisit,
            fallback_count = Director.FallbackCount,
            avatar_animation_process_us_average = Teacher.AverageAnimationProcessUs,
            avatar_viseme_source = "synthetic_benchmark_timeline",
            video_encoding_measured = false,
        };
        string reportPath = Path.Combine(OutputDirectory, "renderer-scene-tour.json");
        File.WriteAllText(reportPath, JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }));
        GD.Print($"GOVOR_SCENE_TOUR_PASS:{reportPath}");
        GetTree().Quit();
    }

    private static double Percentile(double[] sorted, double fraction)
    {
        if (sorted.Length == 0)
        {
            return 0;
        }
        int index = Math.Clamp((int)Math.Ceiling(sorted.Length * fraction) - 1, 0, sorted.Length - 1);
        return sorted[index];
    }

    private static AvatarAnimationPayload BenchmarkAnimation()
    {
        return new AvatarAnimationPayload(
            2_000_000,
            "speaking",
            "encouraging",
            "provider_phoneme_alignment",
            [
                new SpeechEnergySamplePayload(0, 180),
                new SpeechEnergySamplePayload(400_000, 820),
                new SpeechEnergySamplePayload(800_000, 460),
                new SpeechEnergySamplePayload(1_200_000, 950),
                new SpeechEnergySamplePayload(1_600_000, 300),
            ],
            [
                new VisemeCuePayload("closed", 0, 300_000),
                new VisemeCuePayload("open", 300_000, 800_000),
                new VisemeCuePayload("round", 800_000, 1_300_000),
                new VisemeCuePayload("wide", 1_300_000, 2_000_000),
            ]);
    }
}
