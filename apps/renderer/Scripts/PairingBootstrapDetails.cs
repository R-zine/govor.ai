using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.RegularExpressions;

namespace Govor.Renderer;

public sealed record PairingBootstrapDetails(
    string ControlHost,
    string MediaHost,
    string PairingCode,
    string CertificateSha256,
    long ExpiresAtUnix)
{
    private static readonly Regex HostPattern = new(
        "^[A-Za-z0-9.-]{1,253}$",
        RegexOptions.CultureInvariant);
    private static readonly Regex FingerprintPattern = new(
        "^[0-9A-F]{64}$",
        RegexOptions.CultureInvariant);
    private static readonly Regex PairingCodePattern = new(
        "^[0-9]{8}$",
        RegexOptions.CultureInvariant);
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = false,
        UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow,
    };

    public static PairingBootstrapDetails Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > 2_048)
        {
            throw new InvalidDataException("The pairing bootstrap is too large.");
        }

        BootstrapEnvelope envelope = JsonSerializer.Deserialize<BootstrapEnvelope>(json, JsonOptions)
            ?? throw new InvalidDataException("The pairing bootstrap is empty.");
        if (envelope.ProtocolVersion != "1.0" || envelope.MessageType != "pairing.bootstrap" ||
            !Guid.TryParse(envelope.CorrelationId, out Guid correlationId) ||
            correlationId == Guid.Empty || envelope.Payload is null)
        {
            throw new InvalidDataException("The pairing bootstrap envelope is invalid.");
        }

        ValidateHostPort(envelope.Payload.ControlHost);
        ValidateHostPort(envelope.Payload.MediaHost);
        if (string.IsNullOrEmpty(envelope.Payload.PairingCode) ||
            !PairingCodePattern.IsMatch(envelope.Payload.PairingCode))
        {
            throw new InvalidDataException("The pairing code is invalid.");
        }
        if (string.IsNullOrEmpty(envelope.Payload.CertificateSha256) ||
            !FingerprintPattern.IsMatch(envelope.Payload.CertificateSha256))
        {
            throw new InvalidDataException("The certificate fingerprint is invalid.");
        }
        if (envelope.Payload.ExpiresAtUnix is < 1 or > 4_102_444_800L)
        {
            throw new InvalidDataException("The pairing expiry is invalid.");
        }

        return new PairingBootstrapDetails(
            envelope.Payload.ControlHost!,
            envelope.Payload.MediaHost!,
            envelope.Payload.PairingCode,
            envelope.Payload.CertificateSha256,
            envelope.Payload.ExpiresAtUnix);
    }

    public string DisplayFingerprint() => string.Join(
        ":",
        Enumerable.Range(0, CertificateSha256.Length / 2)
            .Select(index => CertificateSha256.Substring(index * 2, 2)));

    private static void ValidateHostPort(string? value)
    {
        if (string.IsNullOrEmpty(value))
        {
            throw new InvalidDataException("A gateway address is invalid.");
        }

        int separator = value.LastIndexOf(':');
        if (value.Length > 259 || separator <= 0 || separator == value.Length - 1 ||
            !HostPattern.IsMatch(value[..separator]) ||
            !int.TryParse(value[(separator + 1)..], out int port) || port is < 1 or > 65_535)
        {
            throw new InvalidDataException("A gateway address is invalid.");
        }
    }

    private sealed record BootstrapEnvelope(
        [property: JsonPropertyName("protocol_version")] string? ProtocolVersion,
        [property: JsonPropertyName("message_type")] string? MessageType,
        [property: JsonPropertyName("correlation_id")] string? CorrelationId,
        [property: JsonPropertyName("payload")] BootstrapPayload? Payload);

    private sealed record BootstrapPayload(
        [property: JsonPropertyName("control_host")] string? ControlHost,
        [property: JsonPropertyName("media_host")] string? MediaHost,
        [property: JsonPropertyName("pairing_code")] string? PairingCode,
        [property: JsonPropertyName("certificate_sha256")] string? CertificateSha256,
        [property: JsonPropertyName("expires_at_unix")] long ExpiresAtUnix);
}
