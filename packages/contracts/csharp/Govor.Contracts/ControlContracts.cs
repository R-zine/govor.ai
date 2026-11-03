using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.RegularExpressions;

namespace Govor.Contracts;

public sealed record LessonCreationDisplayPayload(
    [property: JsonPropertyName("state")] string State,
    [property: JsonPropertyName("message")] string Message)
{
    public void Validate()
    {
        if (State is not ("idle" or "generating" or "created" or "failed") ||
            string.IsNullOrWhiteSpace(Message) || Message.Length > 512)
        {
            throw new InvalidDataException("Invalid lesson creation status.");
        }
    }
}

public sealed record RendererReadyPayload(
    [property: JsonPropertyName("renderer_id")] Guid RendererId,
    [property: JsonPropertyName("renderer_kind")] string RendererKind,
    [property: JsonPropertyName("protocol_version")] string ProtocolVersion);

public sealed record RendererTeacherProfileSelectedPayload(
    [property: JsonPropertyName("profile_id")] string ProfileId)
{
    private static readonly HashSet<string> AllowedProfiles = ["elena", "amira", "daniel"];

    public void Validate()
    {
        if (!AllowedProfiles.Contains(ProfileId))
        {
            throw new InvalidDataException("Teacher profile is not allow-listed.");
        }
    }
}

public sealed record Vector3Payload(
    [property: JsonPropertyName("x")] double X,
    [property: JsonPropertyName("y")] double Y,
    [property: JsonPropertyName("z")] double Z)
{
    public void Validate()
    {
        if (!double.IsFinite(X) || !double.IsFinite(Y) || !double.IsFinite(Z) ||
            Math.Abs(X) > 20 || Math.Abs(Y) > 20 || Math.Abs(Z) > 20)
        {
            throw new InvalidDataException("Scene position is outside the accepted range.");
        }
    }
}

public sealed record SceneObjectPayload(
    [property: JsonPropertyName("instance_id")] string InstanceId,
    [property: JsonPropertyName("asset_id")] string? AssetId,
    [property: JsonPropertyName("position")] Vector3Payload Position,
    [property: JsonPropertyName("yaw_degrees")] double YawDegrees,
    [property: JsonPropertyName("scale")] double Scale,
    [property: JsonPropertyName("primitive")] PrimitivePayload? Primitive = null)
{
    private static readonly HashSet<string> AllowedAssets =
    [
        "airport-bench", "airport-counter", "airport-sign", "airport-suitcase",
        "cafe-chair", "cafe-counter", "cafe-cup", "cafe-table",
        "home-bookshelf", "home-lamp", "home-sofa", "home-table",
        "market-basket", "market-crate", "market-shelf",
    ];

    public void Validate()
    {
        if (string.IsNullOrWhiteSpace(InstanceId) ||
            !Regex.IsMatch(InstanceId, "^[a-z][a-z0-9-]{1,63}$") ||
            (AssetId is null) == (Primitive is null) ||
            (AssetId is not null && !AllowedAssets.Contains(AssetId)) || Position is null)
        {
            throw new InvalidDataException("Scene object identifiers are invalid or not allow-listed.");
        }
        Primitive?.Validate();
        Position.Validate();
        if (!double.IsFinite(YawDegrees) || Math.Abs(YawDegrees) > 360 ||
            !double.IsFinite(Scale) || Scale is < 0.1 or > 5.0)
        {
            throw new InvalidDataException("Scene object transform is outside the accepted range.");
        }
    }
}

public sealed record PrimitivePayload(
    [property: JsonPropertyName("shape")] string Shape,
    [property: JsonPropertyName("size")] Vector3Payload Size,
    [property: JsonPropertyName("color")] string Color)
{
    private static readonly HashSet<string> Shapes = ["box", "cylinder", "sphere"];

    public void Validate()
    {
        if (Size is null || !Shapes.Contains(Shape) ||
            !Regex.IsMatch(Color ?? string.Empty, "^#[0-9A-Fa-f]{6}$") ||
            !double.IsFinite(Size.X) || !double.IsFinite(Size.Y) || !double.IsFinite(Size.Z) ||
            Size.X is < 0.05 or > 20 || Size.Y is < 0.05 or > 20 || Size.Z is < 0.05 or > 20 ||
            (Shape == "cylinder" && Math.Abs(Size.X - Size.Z) > 0.001))
        {
            throw new InvalidDataException("Scene primitive is invalid.");
        }
    }
}

public sealed record SceneSpecificationPayload(
    [property: JsonPropertyName("scene_id")] string SceneId,
    [property: JsonPropertyName("environment_id")] string EnvironmentId,
    [property: JsonPropertyName("camera_preset")] string CameraPreset,
    [property: JsonPropertyName("lighting_preset")] string LightingPreset,
    [property: JsonPropertyName("transition")] string Transition,
    [property: JsonPropertyName("avatar_position")] Vector3Payload AvatarPosition,
    [property: JsonPropertyName("avatar_yaw_degrees")] double AvatarYawDegrees,
    [property: JsonPropertyName("objects")] IReadOnlyList<SceneObjectPayload> Objects)
{
    private static readonly HashSet<string> Cameras = ["counter", "conversation", "wide"];
    private static readonly HashSet<string> Lighting = ["warm", "daylight", "terminal", "home"];
    private static readonly HashSet<string> Transitions = ["fade", "cut"];

    public void Validate()
    {
        if (!IsSlug(SceneId) || !IsSlug(EnvironmentId) ||
            !Cameras.Contains(CameraPreset) ||
            !Lighting.Contains(LightingPreset) || !Transitions.Contains(Transition))
        {
            throw new InvalidDataException("Scene specification identifiers are invalid.");
        }
        if (AvatarPosition is null || Objects is null || Objects.Count is < 1 or > 64 ||
            !double.IsFinite(AvatarYawDegrees) || Math.Abs(AvatarYawDegrees) > 360)
        {
            throw new InvalidDataException("Scene specification bounds are invalid.");
        }
        AvatarPosition.Validate();
        var instanceIds = new HashSet<string>(StringComparer.Ordinal);
        foreach (SceneObjectPayload item in Objects)
        {
            item.Validate();
            if (!instanceIds.Add(item.InstanceId))
            {
                throw new InvalidDataException("Scene object instance IDs must be unique.");
            }
        }
    }

    private static bool IsSlug(string value) =>
        !string.IsNullOrWhiteSpace(value) && value.Length <= 64 &&
        Regex.IsMatch(value, "^[a-z][a-z0-9-]{2,63}$");
}

public sealed record SpeechEnergySamplePayload(
    [property: JsonPropertyName("media_time_us")] long MediaTimeUs,
    [property: JsonPropertyName("level_milli")] int LevelMilli);

public sealed record VisemeCuePayload(
    [property: JsonPropertyName("viseme")] string Viseme,
    [property: JsonPropertyName("start_us")] long StartUs,
    [property: JsonPropertyName("end_us")] long EndUs);

public sealed record AvatarAnimationPayload(
    [property: JsonPropertyName("duration_us")] long DurationUs,
    [property: JsonPropertyName("gesture")] string Gesture,
    [property: JsonPropertyName("expression")] string Expression,
    [property: JsonPropertyName("viseme_source")] string VisemeSource,
    [property: JsonPropertyName("speech_energy")] IReadOnlyList<SpeechEnergySamplePayload> SpeechEnergy,
    [property: JsonPropertyName("visemes")] IReadOnlyList<VisemeCuePayload> Visemes)
{
    private static readonly HashSet<string> AllowedVisemes =
        ["silence", "closed", "open", "wide", "round", "teeth"];

    public void Validate()
    {
        if (DurationUs is <= 0 or > 30_000_000 || Gesture != "speaking" ||
            Expression != "encouraging" || VisemeSource is not ("provider_phoneme_alignment" or "none") ||
            SpeechEnergy is null || SpeechEnergy.Count is < 1 or > 768 ||
            Visemes is null || Visemes.Count > 2_048)
        {
            throw new InvalidDataException("Avatar animation metadata is invalid.");
        }

        long previousEnergyTime = -1;
        foreach (SpeechEnergySamplePayload sample in SpeechEnergy)
        {
            if (sample.MediaTimeUs <= previousEnergyTime || sample.MediaTimeUs > DurationUs ||
                sample.LevelMilli is < 0 or > 1_000)
            {
                throw new InvalidDataException("Speech energy timeline is invalid.");
            }
            previousEnergyTime = sample.MediaTimeUs;
        }

        long previousEnd = 0;
        foreach (VisemeCuePayload cue in Visemes)
        {
            if (!AllowedVisemes.Contains(cue.Viseme) || cue.StartUs < previousEnd ||
                cue.EndUs <= cue.StartUs || cue.EndUs > DurationUs)
            {
                throw new InvalidDataException("Viseme timeline is invalid.");
            }
            previousEnd = cue.EndUs;
        }
        if (VisemeSource == "none" && Visemes.Count > 0)
        {
            throw new InvalidDataException("Visemes require provider phoneme alignment.");
        }
    }
}

public sealed record RendererCommandPayload(
    [property: JsonPropertyName("session_id")] Guid SessionId,
    [property: JsonPropertyName("command_id")] Guid CommandId,
    [property: JsonPropertyName("action")] string Action,
    [property: JsonPropertyName("media_start_us")] long MediaStartUs,
    [property: JsonPropertyName("duration_us")] long? DurationUs,
    [property: JsonPropertyName("scene")] SceneSpecificationPayload? Scene = null,
    [property: JsonPropertyName("avatar_animation")] AvatarAnimationPayload? AvatarAnimation = null)
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
        if (Scene is not null)
        {
            if (Action != "session_started")
            {
                throw new InvalidDataException("Scene specifications are accepted only at session start.");
            }
            Scene.Validate();
        }
        if (AvatarAnimation is not null)
        {
            if (Action != "teacher_speaking" || DurationUs != AvatarAnimation.DurationUs)
            {
                throw new InvalidDataException("Avatar animation does not match the renderer command.");
            }
            AvatarAnimation.Validate();
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
