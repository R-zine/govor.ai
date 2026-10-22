using System.IO.MemoryMappedFiles;
using System.Text;
using System.Threading;
using Godot;

namespace Govor.Renderer;

/// <summary>
/// Publishes the latest complete Godot SubViewport frame to a Windows-local named mapping.
/// Capture is deliberately bounded: slow readback drops frames rather than creating a queue.
/// </summary>
public partial class SharedMemoryVideoPublisher : Node
{
    private const ulong CaptureSchedulingToleranceUs = 2_000;
    private MemoryMappedFile? _mapping;
    private MemoryMappedViewAccessor? _view;
    private ulong _startedAtUs;
    private ulong _nextCaptureAtUs;
    private long _publishedSequence;
    private long _writerGeneration;
    private int _activeSlot;
    private bool _bridgeUnavailable;

    public SubViewport? SourceViewport { get; set; }

    public bool IsReady => _view is not null && !_bridgeUnavailable;

    public override void _Ready()
    {
        if (!OperatingSystem.IsWindows())
        {
            GD.PushWarning("The renderer shared-memory bridge is currently Windows-only.");
            SetProcess(false);
            return;
        }

        try
        {
            _mapping = MemoryMappedFile.CreateOrOpen(
                RendererBridgeProtocol.VideoMapName,
                RendererBridgeProtocol.VideoMapSize,
                MemoryMappedFileAccess.ReadWrite);
            _view = _mapping.CreateViewAccessor(
                0,
                RendererBridgeProtocol.VideoMapSize,
                MemoryMappedFileAccess.ReadWrite);
            _writerGeneration = CreateWriterGeneration();
            _startedAtUs = Time.GetTicksUsec();
            _nextCaptureAtUs = _startedAtUs;
            InitializeHeader();
        }
        catch (Exception error)
        {
            _bridgeUnavailable = true;
            GD.PushError($"Unable to initialize the local video bridge: {error.Message}");
            DisposeMapping();
        }
    }

    public override void _Process(double delta)
    {
        _ = delta;
        if (!IsReady || SourceViewport is null)
        {
            return;
        }

        ulong nowUs = Time.GetTicksUsec();
        if (nowUs + CaptureSchedulingToleranceUs < _nextCaptureAtUs)
        {
            return;
        }

        ulong frameIntervalUs = 1_000_000UL / RendererBridgeProtocol.TargetFrameRate;
        _nextCaptureAtUs += frameIntervalUs;
        if (nowUs > _nextCaptureAtUs + frameIntervalUs)
        {
            // Bound catch-up after a real stall; never queue multiple synchronous GPU readbacks.
            _nextCaptureAtUs = nowUs + frameIntervalUs;
        }
        Image image = SourceViewport.GetTexture().GetImage();
        try
        {
            if (image.IsEmpty())
            {
                return;
            }

            if (image.GetWidth() != RendererBridgeProtocol.CaptureWidth ||
                image.GetHeight() != RendererBridgeProtocol.CaptureHeight)
            {
                FailBridge($"Unexpected viewport size: {image.GetWidth()}x{image.GetHeight()}.");
                return;
            }

            if (image.GetFormat() != Image.Format.Rgba8)
            {
                image.Convert(Image.Format.Rgba8);
            }

            byte[] frame = image.GetData();
            if (frame.Length != RendererBridgeProtocol.VideoPayloadSize)
            {
                FailBridge($"Unexpected renderer frame size: {frame.Length} bytes.");
                return;
            }

            PublishFrame(frame, checked((long)(nowUs - _startedAtUs)));
        }
        finally
        {
            image.Dispose();
        }
    }

    public override void _ExitTree()
    {
        DisposeMapping();
    }

    private void InitializeHeader()
    {
        MemoryMappedViewAccessor view = _view!;
        byte[] magic = Encoding.ASCII.GetBytes("GOVVID01");
        view.WriteArray(0, magic, 0, magic.Length);
        view.Write(8, RendererBridgeProtocol.VideoVersion);
        view.Write(12, RendererBridgeProtocol.VideoHeaderSize);
        view.Write(16, RendererBridgeProtocol.CaptureWidth);
        view.Write(20, RendererBridgeProtocol.CaptureHeight);
        view.Write(24, RendererBridgeProtocol.VideoStride);
        view.Write(28, RendererBridgeProtocol.VideoPayloadSize);
        view.Write(RendererBridgeProtocol.VideoSequenceOffset, 0L);
        view.Write(RendererBridgeProtocol.VideoMediaTimeOffset, 0L);
        view.Write(48, 0); // Godot Image data is published top-to-bottom.
        view.Write(52, RendererBridgeProtocol.VideoRgbaFormat);
        view.Write(56, _writerGeneration);
    }

    private void PublishFrame(byte[] pixels, long mediaTimeUs)
    {
        MemoryMappedViewAccessor view = _view!;
        int targetSlot = (_activeSlot + 1) % RendererBridgeProtocol.VideoSlotCount;
        long payloadOffset = RendererBridgeProtocol.VideoHeaderSize +
            (long)targetSlot * RendererBridgeProtocol.VideoPayloadSize;
        long inProgress = _publishedSequence + 1;
        long complete = _publishedSequence + 2;

        // Keep the currently published slot immutable while the next frame is copied. The
        // header commit below is tiny compared with a full 1280x720 RGBA transfer, so readers
        // no longer discard roughly half the publications after colliding with a long write.
        view.WriteArray(payloadOffset, pixels, 0, pixels.Length);
        Thread.MemoryBarrier();
        view.Write(RendererBridgeProtocol.VideoSequenceOffset, inProgress);
        Thread.MemoryBarrier();
        view.Write(RendererBridgeProtocol.VideoMediaTimeOffset, mediaTimeUs);
        view.Write(
            RendererBridgeProtocol.VideoFlagsOffset,
            targetSlot << RendererBridgeProtocol.VideoActiveSlotShift);
        Thread.MemoryBarrier();
        view.Write(RendererBridgeProtocol.VideoSequenceOffset, complete);
        _publishedSequence = complete;
        _activeSlot = targetSlot;
    }

    private void FailBridge(string message)
    {
        _bridgeUnavailable = true;
        GD.PushError(message + " Video publication stopped.");
    }

    private static long CreateWriterGeneration()
    {
        long generation = BitConverter.ToInt64(Guid.NewGuid().ToByteArray(), 0);
        return generation == 0 ? 1 : generation;
    }

    private void DisposeMapping()
    {
        _view?.Dispose();
        _view = null;
        _mapping?.Dispose();
        _mapping = null;
    }
}
