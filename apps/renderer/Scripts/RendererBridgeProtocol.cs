namespace Govor.Renderer;

/// <summary>
/// Fixed, versioned layout shared only between the Windows renderer and the local media peer.
/// This is process-local transport, not a network contract.
/// </summary>
public static class RendererBridgeProtocol
{
    public const string VideoMapName = "govor.ai.renderer.video.v1";
    public const string AudioMapName = "govor.ai.renderer.audio.v1";

    public const int CaptureWidth = 1280;
    public const int CaptureHeight = 720;
    public const int TargetFrameRate = 30;

    public const int VideoHeaderSize = 64;
    public const int VideoBytesPerPixel = 4;
    public const int VideoStride = CaptureWidth * VideoBytesPerPixel;
    public const int VideoPayloadSize = VideoStride * CaptureHeight;
    public const int VideoMapSize = VideoHeaderSize + VideoPayloadSize;
    public const int VideoSequenceOffset = 32;
    public const int VideoMediaTimeOffset = 40;
    public const int VideoRgbaFormat = 1;

    public const int AudioSampleRate = 48_000;
    public const int AudioChannels = 1;
    public const int AudioSamplesPerBlock = 960;
    public const int AudioBlockCapacity = 64;
    public const int AudioHeaderSize = 64;
    public const int AudioSlotHeaderSize = 24;
    public const int AudioPayloadSize = AudioSamplesPerBlock * sizeof(short);
    public const int AudioSlotSize = AudioSlotHeaderSize + AudioPayloadSize;
    public const int AudioMapSize = AudioHeaderSize + AudioBlockCapacity * AudioSlotSize;
    public const int AudioWriteSequenceOffset = 40;
}
