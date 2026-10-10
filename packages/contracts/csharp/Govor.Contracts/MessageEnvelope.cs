using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.RegularExpressions;

namespace Govor.Contracts;

public sealed record MessageEnvelope(
    [property: JsonPropertyName("protocol_version")] string ProtocolVersion,
    [property: JsonPropertyName("message_type")] string MessageType,
    [property: JsonPropertyName("correlation_id")] Guid CorrelationId,
    [property: JsonPropertyName("payload")] JsonElement Payload)
{
    public const string CurrentProtocolVersion = "1.0";

    public void Validate()
    {
        if (ProtocolVersion != CurrentProtocolVersion)
        {
            throw new InvalidDataException($"Unsupported protocol version: {ProtocolVersion}");
        }

        if (string.IsNullOrWhiteSpace(MessageType) ||
            !Regex.IsMatch(MessageType, "^[a-z][a-z0-9_.-]{0,63}$", RegexOptions.CultureInvariant))
        {
            throw new InvalidDataException("Message type does not match the version 1 contract.");
        }

        if (CorrelationId == Guid.Empty)
        {
            throw new InvalidDataException("A non-empty correlation identifier is required.");
        }

        if (Payload.ValueKind != JsonValueKind.Object)
        {
            throw new InvalidDataException("Payload must be a JSON object.");
        }
    }
}
