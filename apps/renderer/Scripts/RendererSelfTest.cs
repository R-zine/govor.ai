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

        const string pairingBootstrap =
            """{"protocol_version":"1.0","message_type":"pairing.bootstrap","correlation_id":"b278aa30-e921-436f-8b46-a70a53d9cc89","payload":{"control_host":"192.168.1.10:8765","media_host":"192.168.1.10:8766","pairing_code":"12345678","certificate_sha256":"0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF","expires_at_unix":4102444800}}""";
        PairingBootstrapDetails pairing = PairingBootstrapDetails.Parse(pairingBootstrap);
        if (pairing.ControlHost != "192.168.1.10:8765" ||
            pairing.MediaHost != "192.168.1.10:8766" ||
            pairing.PairingCode != "12345678" ||
            pairing.DisplayFingerprint().Split(':').Length != 32)
        {
            throw new InvalidOperationException("The host pairing bootstrap was not parsed correctly.");
        }

        try
        {
            PairingBootstrapDetails.Parse(pairingBootstrap.Replace(
                "\"payload\":",
                "\"unexpected\":true,\"payload\":",
                StringComparison.Ordinal));
            throw new InvalidOperationException("Unknown host pairing fields were accepted.");
        }
        catch (JsonException)
        {
            // Closed bootstrap payloads reject unrecognized fields.
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

        if (TeacherProfileCatalog.Profiles.Count != 3 ||
            TeacherProfileCatalog.Profiles.Select(profile => profile.Id).Distinct().Count() != 3 ||
            TeacherProfileCatalog.Profiles.Any(profile => !ResourceLoader.Exists(profile.AssetPath)))
        {
            throw new InvalidOperationException("The selectable teacher profile catalog is incomplete.");
        }
        new RendererTeacherProfileSelectedPayload("daniel").Validate();
        try
        {
            new RendererTeacherProfileSelectedPayload("../../arbitrary").Validate();
            throw new InvalidOperationException("An arbitrary teacher profile was accepted.");
        }
        catch (InvalidDataException)
        {
            // The cross-process selection is closed to the three installed profiles.
        }
        string managementCommand = HostManagementActions.ResolveCommand(
            Path.GetTempPath(),
            "Create-Lesson.cmd");
        if (Path.GetFileName(managementCommand) != "Create-Lesson.cmd")
        {
            throw new InvalidOperationException("The host management allow-list is invalid.");
        }
        try
        {
            HostManagementActions.ResolveCommand(Path.GetTempPath(), "arbitrary.cmd");
            throw new InvalidOperationException("An arbitrary host management command was accepted.");
        }
        catch (InvalidDataException)
        {
            // Management actions resolve only exact package-owned entry points.
        }

        IReadOnlyList<SceneSpecificationPayload> scenes = DynamicSceneDirector.TourScenes();
        if (scenes.Count != 4 || scenes.Select(scene => scene.EnvironmentId).Distinct().Count() != 4)
        {
            throw new InvalidOperationException("The four deterministic environment recipes are unavailable.");
        }
        foreach (SceneSpecificationPayload scene in scenes)
        {
            scene.Validate();
            if (!PhotographicBackdropCatalog.HasBackdrop(scene.EnvironmentId))
            {
                throw new InvalidOperationException(
                    $"No audited photographic backdrop is available for {scene.EnvironmentId}.");
            }
        }
        if (PhotographicBackdropCatalog.BackdropCount != 4)
        {
            throw new InvalidOperationException("The photographic backdrop catalog is incomplete.");
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
