using System.Text.Json;
using System.Text.Json.Serialization;

namespace Govor.Contracts;

public sealed record RendererReadyPayload(
    [property: JsonPropertyName("renderer_id")] Guid RendererId,
    [property: JsonPropertyName("renderer_kind")] string RendererKind,
    [property: JsonPropertyName("protocol_version")] string ProtocolVersion);

public sealed record RendererCommandPayload(
    [property: JsonPropertyName("session_id")] Guid SessionId,
    [property: JsonPropertyName("command_id")] Guid CommandId,
    [property: JsonPropertyName("action")] string Action,
    [property: JsonPropertyName("media_start_us")] long MediaStartUs,
    [property: JsonPropertyName("duration_us")] long? DurationUs)
{
    private static readonly HashSet<string> AllowedActions =
    [
        "session_started",
        "teacher_speaking",
        "awaiting_learner",
        "recording",
        "processing",
        "reset",
    ];

    public void Validate()
    {
        if (SessionId == Guid.Empty || CommandId == Guid.Empty)
        {
            throw new InvalidDataException("Renderer command identifiers must be non-empty UUIDs.");
        }

        if (!AllowedActions.Contains(Action))
        {
            throw new InvalidDataException("Renderer action is not allow-listed.");
        }

        if (MediaStartUs < 0 || DurationUs is <= 0 or > 30_000_000)
        {
            throw new InvalidDataException("Renderer media timing is outside the accepted range.");
        }
    }
}

public sealed record RendererAckPayload(
    [property: JsonPropertyName("command_id")] Guid CommandId,
    [property: JsonPropertyName("applied")] bool Applied);

public sealed record PronunciationPayload(
    [property: JsonPropertyName("word")] string Word,
    [property: JsonPropertyName("start_char")] int StartChar,
    [property: JsonPropertyName("end_char")] int EndChar,
    [property: JsonPropertyName("ipa")] string Ipa,
    [property: JsonPropertyName("locale")] string Locale,
    [property: JsonPropertyName("explanation")] string? Explanation);

public sealed record WordAlignmentPayload(
    [property: JsonPropertyName("word_index")] int WordIndex,
    [property: JsonPropertyName("start_us")] long StartUs,
    [property: JsonPropertyName("end_us")] long EndUs);

public sealed record PhonemeAlignmentPayload(
    [property: JsonPropertyName("word_index")] int WordIndex,
    [property: JsonPropertyName("symbol")] string Symbol,
    [property: JsonPropertyName("start_us")] long StartUs,
    [property: JsonPropertyName("end_us")] long EndUs);

public sealed record LessonProgressPayload(
    [property: JsonPropertyName("scenario_id")] string ScenarioId,
    [property: JsonPropertyName("scenario_title")] string ScenarioTitle,
    [property: JsonPropertyName("exercise_number")] int ExerciseNumber,
    [property: JsonPropertyName("exercise_count")] int ExerciseCount,
    [property: JsonPropertyName("successful_exercises")] int SuccessfulExercises,
    [property: JsonPropertyName("attempts_on_exercise")] int AttemptsOnExercise,
    [property: JsonPropertyName("difficulty")] string Difficulty,
    [property: JsonPropertyName("status")] string Status,
    [property: JsonPropertyName("resumed")] bool Resumed,
    [property: JsonPropertyName("difficulty_change_reason")] string? DifficultyChangeReason);

public sealed record TeacherTurnPayload(
    [property: JsonPropertyName("session_id")] Guid SessionId,
    [property: JsonPropertyName("turn_id")] Guid TurnId,
    [property: JsonPropertyName("text")] string Text,
    [property: JsonPropertyName("locale")] string Locale,
    [property: JsonPropertyName("provider_id")] string ProviderId,
    [property: JsonPropertyName("audio_format")] string AudioFormat,
    [property: JsonPropertyName("sample_rate_hz")] int SampleRateHz,
    [property: JsonPropertyName("duration_us")] long DurationUs,
    [property: JsonPropertyName("audio_base64")] string AudioBase64,
    [property: JsonPropertyName("pronunciations")] IReadOnlyList<PronunciationPayload> Pronunciations,
    [property: JsonPropertyName("word_alignment")] IReadOnlyList<WordAlignmentPayload>? WordAlignment,
    [property: JsonPropertyName("phoneme_alignment")] IReadOnlyList<PhonemeAlignmentPayload>? PhonemeAlignment,
    [property: JsonPropertyName("fallback_used")] bool FallbackUsed,
    [property: JsonPropertyName("lesson_progress")] LessonProgressPayload? LessonProgress);

public sealed record TeacherWordReplayRequestPayload(
    [property: JsonPropertyName("session_id")] Guid SessionId,
    [property: JsonPropertyName("turn_id")] Guid TurnId,
    [property: JsonPropertyName("word_index")] int WordIndex,
    [property: JsonPropertyName("playback_rate")] float PlaybackRate);

public sealed record TeacherWordAudioPayload(
    [property: JsonPropertyName("session_id")] Guid SessionId,
    [property: JsonPropertyName("turn_id")] Guid TurnId,
    [property: JsonPropertyName("word_index")] int WordIndex,
    [property: JsonPropertyName("word")] string Word,
    [property: JsonPropertyName("locale")] string Locale,
    [property: JsonPropertyName("provider_id")] string ProviderId,
    [property: JsonPropertyName("audio_format")] string AudioFormat,
    [property: JsonPropertyName("sample_rate_hz")] int SampleRateHz,
    [property: JsonPropertyName("duration_us")] long DurationUs,
    [property: JsonPropertyName("audio_base64")] string AudioBase64,
    [property: JsonPropertyName("fallback_used")] bool FallbackUsed);

public static class ControlContractCodec
{
    public static readonly JsonSerializerOptions Options = new()
    {
        PropertyNameCaseInsensitive = false,
        UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow,
    };

    public static MessageEnvelope DecodeEnvelope(string json)
    {
        MessageEnvelope envelope = JsonSerializer.Deserialize<MessageEnvelope>(json, Options)
            ?? throw new InvalidDataException("Control envelope is empty.");
        envelope.Validate();
        return envelope;
    }

    public static T DecodePayload<T>(MessageEnvelope envelope)
    {
        T? payload = envelope.Payload.Deserialize<T>(Options);
        return payload ?? throw new InvalidDataException("Control payload is empty.");
    }

    public static string EncodeEnvelope<T>(string messageType, Guid correlationId, T payload)
    {
        JsonElement payloadElement = JsonSerializer.SerializeToElement(payload, Options);
        var envelope = new MessageEnvelope(
            MessageEnvelope.CurrentProtocolVersion,
            messageType,
            correlationId,
            payloadElement);
        envelope.Validate();
        return JsonSerializer.Serialize(envelope, Options);
    }
}
