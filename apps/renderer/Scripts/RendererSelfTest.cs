using System.Text.Json;
using Godot;
using Govor.Contracts;

namespace Govor.Renderer;

internal static class RendererSelfTest
{
    public const string SuccessMarker = "GOVOR_GODOT_SELF_TEST_PASS";

    public static void Run()
    {
        if (RendererBridgeProtocol.VideoMapSize != 3_686_464)
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

        GD.Print(SuccessMarker);
    }
}
