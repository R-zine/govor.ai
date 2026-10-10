using Godot;

namespace Govor.Renderer;

/// <summary>
/// Generates one bounded application-owned signal. The same PCM is played locally and published
/// to the renderer bridge; it never reads the microphone or captures desktop audio.
/// </summary>
public partial class ApplicationToneGenerator : Node
{
    public const double ToneSeconds = 2.0;
    private const double FrequencyHz = 440.0;
    private const double Amplitude = 0.08;
    private const int TotalBlocks =
        (int)(ToneSeconds * RendererBridgeProtocol.AudioSampleRate /
            RendererBridgeProtocol.AudioSamplesPerBlock);

    private SharedMemoryAudioPublisher? _publisher;
    private AudioStreamPlayer? _player;
    private short[] _toneSamples = Array.Empty<short>();
    private ulong _startedAtUs;
    private int _publishedBlocks;
    private bool _completed;

    public bool PlayLocally { get; set; } = true;
    public bool ExitWhenComplete { get; set; }

    public override void _Ready()
    {
        _publisher = GetNode<SharedMemoryAudioPublisher>("../SharedMemoryAudioPublisher");
        _toneSamples = GenerateTonePcm();
        _startedAtUs = Time.GetTicksUsec();

        if (PlayLocally)
        {
            _player = new AudioStreamPlayer { Name = "TemporaryAudioCheck" };
            AddChild(_player);
            byte[] data = new byte[_toneSamples.Length * sizeof(short)];
            Buffer.BlockCopy(_toneSamples, 0, data, 0, data.Length);
            _player.Stream = new AudioStreamWav
            {
                Format = AudioStreamWav.FormatEnum.Format16Bits,
                MixRate = RendererBridgeProtocol.AudioSampleRate,
                Stereo = false,
                Data = data,
            };
            _player.Play();
        }
    }

    public override void _Process(double delta)
    {
        _ = delta;
        if (_completed)
        {
            return;
        }

        ulong elapsedUs = Time.GetTicksUsec() - _startedAtUs;
        ulong blockDurationUs = 1_000_000UL * RendererBridgeProtocol.AudioSamplesPerBlock /
            RendererBridgeProtocol.AudioSampleRate;
        int dueBlocks = Math.Min(TotalBlocks, (int)(elapsedUs / blockDurationUs) + 1);
        while (_publishedBlocks < dueBlocks)
        {
            short[] block = new short[RendererBridgeProtocol.AudioSamplesPerBlock];
            Array.Copy(
                _toneSamples,
                _publishedBlocks * RendererBridgeProtocol.AudioSamplesPerBlock,
                block,
                0,
                block.Length);
            long mediaTimeUs = (long)_publishedBlocks * RendererBridgeProtocol.AudioSamplesPerBlock *
                1_000_000L / RendererBridgeProtocol.AudioSampleRate;
            _publisher?.PublishMonoPcm16(block, mediaTimeUs);
            _publishedBlocks++;
        }

        if (_publishedBlocks >= TotalBlocks && elapsedUs >= (ulong)(ToneSeconds * 1_000_000.0))
        {
            Complete();
        }
    }

    public override void _ExitTree()
    {
        _player?.Stop();
    }

    internal static short[] GenerateTonePcm()
    {
        int sampleCount = (int)(ToneSeconds * RendererBridgeProtocol.AudioSampleRate);
        short[] samples = new short[sampleCount];
        double phase = 0.0;
        double phaseStep = Math.Tau * FrequencyHz / RendererBridgeProtocol.AudioSampleRate;
        for (int index = 0; index < samples.Length; index++)
        {
            samples[index] = (short)(Math.Sin(phase) * Amplitude * short.MaxValue);
            phase += phaseStep;
            if (phase >= Math.Tau)
            {
                phase -= Math.Tau;
            }
        }

        return samples;
    }

    private void Complete()
    {
        _completed = true;
        _player?.Stop();
        GD.Print("Temporary application tone completed and stopped after two seconds.");
        if (ExitWhenComplete)
        {
            GetTree().Quit();
        }
    }
}
