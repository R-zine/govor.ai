using System.Text.Json;
using Xunit;

namespace Govor.Contracts.Tests;

public sealed class MessageEnvelopeTests
{
    [Fact]
    public void ValidEnvelopePassesValidation()
    {
        using var payloadDocument = JsonDocument.Parse("{}");
        var message = new MessageEnvelope(
            MessageEnvelope.CurrentProtocolVersion,
            "session.start",
            Guid.NewGuid(),
            payloadDocument.RootElement.Clone());

        message.Validate();
    }

    [Fact]
    public void UnknownProtocolVersionIsRejected()
    {
        using var payloadDocument = JsonDocument.Parse("{}");
        var message = new MessageEnvelope(
            "2.0",
            "session.start",
            Guid.NewGuid(),
            payloadDocument.RootElement.Clone());

        var error = Assert.Throws<InvalidDataException>(message.Validate);
        Assert.Contains("Unsupported protocol version", error.Message);
    }

    [Fact]
    public void RendererCommandDeserializesAndValidates()
    {
        string json = File.ReadAllText(
            Path.Combine(AppContext.BaseDirectory, "fixtures", "control-renderer-command.json"));

        MessageEnvelope envelope = ControlContractCodec.DecodeEnvelope(json);
        RendererCommandPayload payload =
            ControlContractCodec.DecodePayload<RendererCommandPayload>(envelope);

        payload.Validate();
        Assert.Equal("teacher_speaking", payload.Action);
        Assert.Equal(150_000, payload.DurationUs);
    }

    [Fact]
    public void UnknownRendererPayloadFieldIsRejected()
    {
        using var payloadDocument = JsonDocument.Parse(
            """{"session_id":"3191d8bd-d30f-488b-a324-cb91f1286745","command_id":"19c369b5-6fca-43ea-bffc-764b51b7e7c2","action":"processing","media_start_us":0,"duration_us":null,"path":"not-allowed"}""");
        var envelope = new MessageEnvelope(
            MessageEnvelope.CurrentProtocolVersion,
            "renderer.command",
            Guid.NewGuid(),
            payloadDocument.RootElement.Clone());

        Assert.Throws<JsonException>(
            () => ControlContractCodec.DecodePayload<RendererCommandPayload>(envelope));
    }

    [Fact]
    public void NonAllowListedRendererActionIsRejected()
    {
        var payload = new RendererCommandPayload(
            Guid.NewGuid(),
            Guid.NewGuid(),
            "run_arbitrary_code",
            0,
            null);

        Assert.Throws<InvalidDataException>(payload.Validate);
    }
}
