using System.IO.MemoryMappedFiles;
using System.Text;
using System.Threading;
using Godot;

namespace Govor.Renderer;

/// <summary>
/// Publishes fixed 20 ms, 48 kHz mono PCM blocks to the bounded renderer-local ring.
/// </summary>
public partial class SharedMemoryAudioPublisher : Node
{
    private MemoryMappedFile? _mapping;
    private MemoryMappedViewAccessor? _view;
    private long _writeSequence;
    private long _writerGeneration;

    public bool IsReady => _view is not null;

    public override void _Ready()
    {
        if (!OperatingSystem.IsWindows())
        {
            GD.PushWarning("The renderer shared-memory bridge is currently Windows-only.");
            return;
        }

        try
        {
            _mapping = MemoryMappedFile.CreateOrOpen(
                RendererBridgeProtocol.AudioMapName,
                RendererBridgeProtocol.AudioMapSize,
                MemoryMappedFileAccess.ReadWrite);
            _view = _mapping.CreateViewAccessor(
                0,
                RendererBridgeProtocol.AudioMapSize,
                MemoryMappedFileAccess.ReadWrite);
            _writerGeneration = CreateWriterGeneration();
            InitializeHeader();
        }
        catch (Exception error)
        {
            GD.PushError($"Unable to initialize the local audio bridge: {error.Message}");
            DisposeMapping();
        }
    }

    public bool PublishMonoPcm16(short[] samples, long mediaTimeUs)
    {
        if (_view is null || samples.Length != RendererBridgeProtocol.AudioSamplesPerBlock)
        {
            return false;
        }

        long sequence = _writeSequence + 1;
        int slotIndex = (int)((sequence - 1) % RendererBridgeProtocol.AudioBlockCapacity);
        long slotOffset = RendererBridgeProtocol.AudioHeaderSize +
            slotIndex * RendererBridgeProtocol.AudioSlotSize;
        _view.Write(slotOffset, 0L);
        Thread.MemoryBarrier();
        _view.Write(slotOffset + 8, mediaTimeUs);
        _view.Write(slotOffset + 16, RendererBridgeProtocol.AudioSamplesPerBlock);
        _view.Write(slotOffset + 20, 0);
        _view.WriteArray(
            slotOffset + RendererBridgeProtocol.AudioSlotHeaderSize,
            samples,
            0,
            samples.Length);
        Thread.MemoryBarrier();
        _view.Write(slotOffset, sequence);
        _view.Write(RendererBridgeProtocol.AudioWriteSequenceOffset, sequence);
        _view.Write(48, mediaTimeUs);
        _writeSequence = sequence;
        return true;
    }

    public override void _ExitTree()
    {
        DisposeMapping();
    }

    private void InitializeHeader()
    {
        MemoryMappedViewAccessor view = _view!;
        byte[] magic = Encoding.ASCII.GetBytes("GOVAUD01");
        view.WriteArray(0, magic, 0, magic.Length);
        view.Write(8, 1);
        view.Write(12, RendererBridgeProtocol.AudioHeaderSize);
        view.Write(16, RendererBridgeProtocol.AudioSampleRate);
        view.Write(20, RendererBridgeProtocol.AudioChannels);
        view.Write(24, RendererBridgeProtocol.AudioSamplesPerBlock);
        view.Write(28, RendererBridgeProtocol.AudioBlockCapacity);
        view.Write(32, RendererBridgeProtocol.AudioSlotSize);
        view.Write(36, 0);
        view.Write(RendererBridgeProtocol.AudioWriteSequenceOffset, 0L);
        view.Write(48, 0L);
        view.Write(56, _writerGeneration);
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
