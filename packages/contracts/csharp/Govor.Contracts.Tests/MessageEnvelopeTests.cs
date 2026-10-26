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
        Assert.Equal("provider_phoneme_alignment", payload.AvatarAnimation?.VisemeSource);
        Assert.Equal("closed", payload.AvatarAnimation?.Visemes[0].Viseme);
    }

    [Fact]
    public void TeacherTurnDeserializesPronunciationAndAlignment()
    {
        string json = File.ReadAllText(
            Path.Combine(AppContext.BaseDirectory, "fixtures", "control-teacher-turn.json"));

        MessageEnvelope envelope = ControlContractCodec.DecodeEnvelope(json);
        TeacherTurnPayload payload = ControlContractCodec.DecodePayload<TeacherTurnPayload>(envelope);

        Assert.Equal("en-GB", payload.Locale);
        Assert.Equal("ˈwɛlkəm", payload.Pronunciations[0].Ipa);
        Assert.Equal(0, payload.WordAlignment?[0].WordIndex);
        Assert.False(payload.FallbackUsed);
        Assert.Equal("cafe-ordering", payload.LessonProgress!.ScenarioId);
        Assert.Equal(1, payload.LessonProgress.ExerciseNumber);
        Assert.Equal("intermediate", payload.LessonProgress.Difficulty);
    }

    [Fact]
    public void WordReplayRequestAndAudioFixturesDeserialize()
    {
        string requestJson = File.ReadAllText(
            Path.Combine(AppContext.BaseDirectory, "fixtures", "control-word-replay-request.json"));
        string audioJson = File.ReadAllText(
            Path.Combine(AppContext.BaseDirectory, "fixtures", "control-word-audio.json"));

        TeacherWordReplayRequestPayload request = ControlContractCodec.DecodePayload<TeacherWordReplayRequestPayload>(
            ControlContractCodec.DecodeEnvelope(requestJson));
        TeacherWordAudioPayload audio = ControlContractCodec.DecodePayload<TeacherWordAudioPayload>(
            ControlContractCodec.DecodeEnvelope(audioJson));

        Assert.Equal(0.75f, request.PlaybackRate);
        Assert.Equal(request.TurnId, audio.TurnId);
        Assert.Equal(request.WordIndex, audio.WordIndex);
        Assert.Equal("Welcome", audio.Word);
        Assert.False(audio.FallbackUsed);
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
    public void TeacherProfileSelectionIsClosed()
    {
        new RendererTeacherProfileSelectedPayload("amira").Validate();
        Assert.Throws<InvalidDataException>(
            () => new RendererTeacherProfileSelectedPayload("../../arbitrary").Validate());
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

    [Fact]
    public void CustomPrimitiveSceneIsAccepted()
    {
        var scene = new SceneSpecificationPayload(
            "hotel-lobby-v1",
            "hotel-lobby",
            "wide",
            "warm",
            "fade",
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

        scene.Validate();
    }

    [Fact]
    public void NonAllowListedSceneAssetIsRejected()
    {
        var scene = new SceneSpecificationPayload(
            "unsafe-scene",
            "cafe",
            "counter",
            "warm",
            "fade",
            new Vector3Payload(0, 0, 0),
            0,
            [
                new SceneObjectPayload(
                    "unsafe-object",
                    "../../arbitrary.glb",
                    new Vector3Payload(0, 0, 0),
                    0,
                    1),
            ]);

        Assert.Throws<InvalidDataException>(scene.Validate);
    }
}
