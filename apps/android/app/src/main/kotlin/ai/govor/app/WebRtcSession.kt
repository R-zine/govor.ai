package ai.govor.app

import android.content.Context
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import org.json.JSONObject
import org.webrtc.AudioSource
import org.webrtc.AudioTrack
import org.webrtc.DataChannel
import org.webrtc.DefaultVideoDecoderFactory
import org.webrtc.DefaultVideoEncoderFactory
import org.webrtc.EglBase
import org.webrtc.IceCandidate
import org.webrtc.MediaConstraints
import org.webrtc.MediaStream
import org.webrtc.MediaStreamTrack
import org.webrtc.PeerConnection
import org.webrtc.PeerConnectionFactory
import org.webrtc.RtpReceiver
import org.webrtc.RtpTransceiver
import org.webrtc.SdpObserver
import org.webrtc.SessionDescription
import org.webrtc.SurfaceViewRenderer
import org.webrtc.VideoTrack
import org.webrtc.audio.JavaAudioDeviceModule
import java.util.UUID
import java.util.concurrent.TimeUnit

enum class MediaConnectionStatus {
    DISCONNECTED,
    SIGNALING,
    CONNECTING,
    CONNECTED,
    FAILED,
}

class WebRtcSession(private val context: Context) : PeerConnection.Observer {
    private val eglBase = EglBase.create()
    private val audioDeviceModule = JavaAudioDeviceModule.builder(context).createAudioDeviceModule()
    private val factory: PeerConnectionFactory
    private var httpClient: OkHttpClient? = null

    private var socket: WebSocket? = null
    private var peerConnection: PeerConnection? = null
    private var audioSource: AudioSource? = null
    private var microphoneTrack: AudioTrack? = null
    private var renderer: SurfaceViewRenderer? = null
    private var offerSent = false

    private val mutableStatus = MutableStateFlow(MediaConnectionStatus.DISCONNECTED)
    val status: StateFlow<MediaConnectionStatus> = mutableStatus

    private val mutableError = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = mutableError

    val eglContext: EglBase.Context
        get() = eglBase.eglBaseContext

    init {
        PeerConnectionFactory.initialize(
            PeerConnectionFactory.InitializationOptions.builder(context)
                .setEnableInternalTracer(false)
                .createInitializationOptions(),
        )
        factory = PeerConnectionFactory.builder()
            .setAudioDeviceModule(audioDeviceModule)
            .setVideoEncoderFactory(DefaultVideoEncoderFactory(eglContext, true, true))
            .setVideoDecoderFactory(DefaultVideoDecoderFactory(eglContext))
            .createPeerConnectionFactory()
    }

    fun connect(
        host: String,
        credential: String,
        secure: Boolean = false,
        deviceId: String? = null,
        certificateFingerprint: String? = null,
    ) {
        disconnect()
        if (credential.length !in 32..256) {
            fail("Pairing credential is invalid.")
            return
        }
        if (secure && (deviceId == null || certificateFingerprint == null)) {
            fail("Secure pairing information is incomplete.")
            return
        }
        val normalizedHost = GatewaySecurity.normalizeHost(host)
        if (normalizedHost.isBlank()) {
            fail("Enter the Windows host address.")
            return
        }

        val rtcConfiguration = PeerConnection.RTCConfiguration(emptyList()).apply {
            sdpSemantics = PeerConnection.SdpSemantics.UNIFIED_PLAN
            // Signaling sends one SDP blob after candidate gathering; trickle ICE is not wired yet.
            continualGatheringPolicy = PeerConnection.ContinualGatheringPolicy.GATHER_ONCE
        }
        peerConnection = factory.createPeerConnection(rtcConfiguration, this)
        if (peerConnection == null) {
            fail("Unable to create the WebRTC peer connection.")
            return
        }

        audioSource = factory.createAudioSource(MediaConstraints())
        microphoneTrack = factory.createAudioTrack("govor-microphone", audioSource).apply {
            setEnabled(false)
        }
        peerConnection?.addTrack(microphoneTrack, listOf("govor"))
        peerConnection?.addTransceiver(
            MediaStreamTrack.MediaType.MEDIA_TYPE_VIDEO,
            RtpTransceiver.RtpTransceiverInit(RtpTransceiver.RtpTransceiverDirection.RECV_ONLY),
        )
        mutableError.value = null
        mutableStatus.value = MediaConnectionStatus.SIGNALING
        val request = try {
            Request.Builder()
                .url("${if (secure) "wss" else "ws"}://$normalizedHost/v1/media/signaling")
                .build()
        } catch (_: IllegalArgumentException) {
            disconnect()
            fail("Enter a valid Windows host and port.")
            return
        }
        httpClient = if (secure) {
            GatewaySecurity.pinnedClient(requireNotNull(certificateFingerprint))
        } else {
            GatewaySecurity.developmentClient()
        }
        socket = requireNotNull(httpClient).newWebSocket(
            request,
            SignalingListener(credential, deviceId),
        )
    }

    fun attachRenderer(view: SurfaceViewRenderer) {
        renderer = view
    }

    fun detachRenderer(view: SurfaceViewRenderer) {
        if (renderer === view) renderer = null
    }

    fun setPushToTalk(active: Boolean) {
        if (mutableStatus.value == MediaConnectionStatus.CONNECTED) {
            microphoneTrack?.setEnabled(active)
        }
    }

    fun disconnect() {
        microphoneTrack?.setEnabled(false)
        socket?.close(1000, "client disconnect")
        socket = null
        peerConnection?.close()
        peerConnection?.dispose()
        peerConnection = null
        microphoneTrack?.dispose()
        microphoneTrack = null
        audioSource?.dispose()
        audioSource = null
        offerSent = false
        httpClient?.dispatcher?.executorService?.shutdown()
        httpClient?.connectionPool?.evictAll()
        httpClient = null
        mutableStatus.value = MediaConnectionStatus.DISCONNECTED
    }

    fun release() {
        disconnect()
        factory.dispose()
        audioDeviceModule.release()
        eglBase.release()
    }

    private fun createOffer() {
        mutableStatus.value = MediaConnectionStatus.CONNECTING
        peerConnection?.createOffer(
            object : SimpleSdpObserver() {
                override fun onCreateSuccess(description: SessionDescription) {
                    peerConnection?.setLocalDescription(
                        object : SimpleSdpObserver() {
                            override fun onSetFailure(error: String) = fail("Local SDP failed: $error")
                        },
                        description,
                    )
                }

                override fun onCreateFailure(error: String) = fail("Offer failed: $error")
            },
            MediaConstraints(),
        )
    }

    private fun sendOfferWhenGathered() {
        if (offerSent) return
        val description = peerConnection?.localDescription ?: return
        offerSent = true
        socket?.send(envelope("webrtc.offer", JSONObject().put("sdp", description.description)))
    }

    private fun applyAnswer(sdp: String) {
        peerConnection?.setRemoteDescription(
            object : SimpleSdpObserver() {
                override fun onSetFailure(error: String) = fail("Remote SDP failed: $error")
            },
            SessionDescription(SessionDescription.Type.ANSWER, sdp),
        )
    }

    private fun envelope(messageType: String, payload: JSONObject): String = JSONObject()
        .put("protocol_version", "1.0")
        .put("message_type", messageType)
        .put("correlation_id", UUID.randomUUID().toString())
        .put("payload", payload)
        .toString()

    private fun fail(message: String) {
        mutableError.value = message
        mutableStatus.value = MediaConnectionStatus.FAILED
    }

    private inner class SignalingListener(
        private val credential: String,
        private val deviceId: String?,
    ) : WebSocketListener() {
        override fun onOpen(webSocket: WebSocket, response: Response) {
            val payload = if (deviceId == null) {
                JSONObject().put("token", credential)
            } else {
                JSONObject().put("device_id", deviceId).put("credential", credential)
            }
            webSocket.send(envelope("auth.request", payload))
        }

        override fun onMessage(webSocket: WebSocket, text: String) {
            runCatching {
                val message = JSONObject(text)
                when (message.getString("message_type")) {
                    "auth.ok" -> createOffer()
                    "webrtc.answer" -> applyAnswer(message.getJSONObject("payload").getString("sdp"))
                    "error" -> fail(message.getJSONObject("payload").getString("message"))
                }
            }.onFailure { fail("Invalid signaling response: ${it.message}") }
        }

        override fun onFailure(webSocket: WebSocket, throwable: Throwable, response: Response?) {
            fail("Signaling failed: ${throwable.message ?: "unknown error"}")
        }

        override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
            if (mutableStatus.value != MediaConnectionStatus.FAILED) {
                mutableStatus.value = MediaConnectionStatus.DISCONNECTED
            }
        }
    }

    override fun onIceGatheringChange(state: PeerConnection.IceGatheringState) {
        if (state == PeerConnection.IceGatheringState.COMPLETE) sendOfferWhenGathered()
    }

    override fun onConnectionChange(state: PeerConnection.PeerConnectionState) {
        when (state) {
            PeerConnection.PeerConnectionState.CONNECTED -> mutableStatus.value = MediaConnectionStatus.CONNECTED
            PeerConnection.PeerConnectionState.FAILED -> fail("WebRTC connection failed.")
            PeerConnection.PeerConnectionState.CLOSED -> mutableStatus.value = MediaConnectionStatus.DISCONNECTED
            else -> Unit
        }
    }

    override fun onTrack(transceiver: RtpTransceiver) {
        val track = transceiver.receiver.track()
        when (track) {
            is VideoTrack -> renderer?.let(track::addSink)
            is AudioTrack -> track.setEnabled(true)
        }
    }

    override fun onSignalingChange(state: PeerConnection.SignalingState) = Unit
    override fun onIceConnectionChange(state: PeerConnection.IceConnectionState) = Unit
    override fun onIceConnectionReceivingChange(receiving: Boolean) = Unit
    override fun onIceCandidate(candidate: IceCandidate) = Unit
    override fun onIceCandidatesRemoved(candidates: Array<out IceCandidate>) = Unit
    override fun onAddStream(stream: MediaStream) = Unit
    override fun onRemoveStream(stream: MediaStream) = Unit
    override fun onDataChannel(channel: DataChannel) = Unit
    override fun onRenegotiationNeeded() = Unit
    override fun onAddTrack(receiver: RtpReceiver, mediaStreams: Array<out MediaStream>) = Unit
}

private open class SimpleSdpObserver : SdpObserver {
    override fun onCreateSuccess(description: SessionDescription) = Unit
    override fun onSetSuccess() = Unit
    override fun onCreateFailure(error: String) = Unit
    override fun onSetFailure(error: String) = Unit
}
