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
    private MemoryMappedFile? _mapping;
    private MemoryMappedViewAccessor? _view;
    private byte[]? _pixels;
    private ulong _startedAtUs;
    private ulong _nextCaptureAtUs;
    private long _publishedSequence;
    private long _writerGeneration;
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
            _pixels = new byte[RendererBridgeProtocol.VideoPayloadSize];
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
        if (!IsReady || SourceViewport is null || _pixels is null)
        {
            return;
        }

        ulong nowUs = Time.GetTicksUsec();
        if (nowUs < _nextCaptureAtUs)
        {
            return;
        }

        _nextCaptureAtUs = nowUs + 1_000_000UL / RendererBridgeProtocol.TargetFrameRate;
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
            if (frame.Length != _pixels.Length)
            {
                FailBridge($"Unexpected renderer frame size: {frame.Length} bytes.");
                return;
            }

            Buffer.BlockCopy(frame, 0, _pixels, 0, frame.Length);
            PublishFrame(nowUs);
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
        view.Write(8, 1);
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

    private void PublishFrame(ulong nowUs)
    {
        MemoryMappedViewAccessor view = _view!;
        byte[] pixels = _pixels!;
        long inProgress = _publishedSequence + 1;
        long complete = _publishedSequence + 2;
        long mediaTimeUs = checked((long)(nowUs - _startedAtUs));
        view.Write(RendererBridgeProtocol.VideoSequenceOffset, inProgress);
        Thread.MemoryBarrier();
        view.Write(RendererBridgeProtocol.VideoMediaTimeOffset, mediaTimeUs);
        view.WriteArray(RendererBridgeProtocol.VideoHeaderSize, pixels, 0, pixels.Length);
        Thread.MemoryBarrier();
        view.Write(RendererBridgeProtocol.VideoSequenceOffset, complete);
        _publishedSequence = complete;
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
