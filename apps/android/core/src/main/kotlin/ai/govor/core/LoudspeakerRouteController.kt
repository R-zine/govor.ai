package ai.govor.core

/** Platform boundary for selecting and restoring Android's communication-audio route. */
interface LoudspeakerRoutePlatform {
    fun captureCurrentRoute()

    fun selectLoudspeaker(): Boolean

    fun restoreCapturedRoute()
}

/**
 * Keeps route capture/restoration balanced across repeated WebRTC callbacks and reconnects.
 *
 * Selection is intentionally reasserted on every activation call because Android or libwebrtc
 * may update communication routing while an audio track is starting.
 */
class LoudspeakerRouteController(private val platform: LoudspeakerRoutePlatform) {
    private var routeCaptured = false

    @Synchronized
    fun activate(): Boolean {
        if (!routeCaptured) {
            val captured = runCatching { platform.captureCurrentRoute() }.isSuccess
            if (!captured) return false
            routeCaptured = true
        }
        return runCatching { platform.selectLoudspeaker() }.getOrDefault(false)
    }

    @Synchronized
    fun deactivate() {
        if (!routeCaptured) return
        try {
            runCatching { platform.restoreCapturedRoute() }
        } finally {
            routeCaptured = false
        }
    }
}
