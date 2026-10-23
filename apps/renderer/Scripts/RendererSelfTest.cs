using System.Text.Json;
using Godot;
using Govor.Contracts;

namespace Govor.Renderer;

internal static class RendererSelfTest
{
    public const string SuccessMarker = "GOVOR_GODOT_SELF_TEST_PASS";

    public static void Run()
    {
        if (RendererBridgeProtocol.VideoMapSize != 7_372_864)
        {
            throw new InvalidOperationException("Unexpected video mapping size.");
        }

        if (RendererBridgeProtocol.AudioMapSize != 124_480)
        {
            throw new InvalidOperationException("Unexpected audio mapping size.");
        }

        short[] tone = ApplicationToneGenerator.GenerateTonePcm();
        if (tone.Length != 96_000 || tone.All(sample => sample == 0))
        {
            throw new InvalidOperationException("The bounded tone PCM is invalid.");
        }

        using var payloadDocument = JsonDocument.Parse(
            """{"session_id":"3191d8bd-d30f-488b-a324-cb91f1286745","command_id":"19c369b5-6fca-43ea-bffc-764b51b7e7c2","action":"teacher_speaking","media_start_us":0,"duration_us":150000}""");
        var envelope = new MessageEnvelope(
            MessageEnvelope.CurrentProtocolVersion,
            "renderer.command",
            Guid.NewGuid(),
            payloadDocument.RootElement.Clone());
        RendererCommandPayload command =
            ControlContractCodec.DecodePayload<RendererCommandPayload>(envelope);
        command.Validate();

        IReadOnlyList<SceneSpecificationPayload> scenes = DynamicSceneDirector.TourScenes();
        if (scenes.Count != 4 || scenes.Select(scene => scene.EnvironmentId).Distinct().Count() != 4)
        {
            throw new InvalidOperationException("The four deterministic environment recipes are unavailable.");
        }
        foreach (SceneSpecificationPayload scene in scenes)
        {
            scene.Validate();
        }

        var customScene = new SceneSpecificationPayload(
            "hotel-lobby-v1",
            "hotel-lobby",
            "wide",
            "warm",
            "cut",
            new Vector3Payload(0, 0, -0.5),
            0,
            [
                new SceneObjectPayload(
                    "front-desk",
                    null,
                    new Vector3Payload(0, 0.55, 1),
                    0,
                    1,
                    new PrimitivePayload("box", new Vector3Payload(4, 1.1, 0.8), "#70452A")),
            ]);
        customScene.Validate();
        Node3D primitive = ProceduralSceneAssetCatalog.CreatePrimitive(customScene.Objects[0].Primitive!);
        primitive.Free();
        Node3D sphere = ProceduralSceneAssetCatalog.CreatePrimitive(
            new PrimitivePayload("sphere", new Vector3Payload(2, 3, 2), "#4B8F8C"));
        try
        {
            if (sphere.GetChild<MeshInstance3D>(0).Scale != new Vector3(2, 3, 2))
            {
                throw new InvalidOperationException("Custom sphere dimensions were not preserved.");
            }
        }
        finally
        {
            sphere.Free();
        }

        Node3D fallback = ProceduralSceneAssetCatalog.Create("missing-self-test", out bool usedFallback);
        try
        {
            if (!usedFallback || fallback.Name != "VisualFallback")
            {
                throw new InvalidOperationException("The missing-asset fallback is not deterministic.");
            }
        }
        finally
        {
            fallback.Free();
        }

        GD.Print(SuccessMarker);
    }
}
