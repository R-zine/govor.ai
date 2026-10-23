package ai.govor.core

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

class LoudspeakerRouteControllerTest {
    @Test
    fun `repeated activation captures once and reasserts the loudspeaker`() {
        val platform = FakeLoudspeakerRoutePlatform()
        val controller = LoudspeakerRouteController(platform)

        assertTrue(controller.activate())
        assertTrue(controller.activate())

        assertEquals(1, platform.captureCount)
        assertEquals(2, platform.selectCount)
        assertEquals(0, platform.restoreCount)
    }

    @Test
    fun `deactivation restores once and a reconnect captures again`() {
        val platform = FakeLoudspeakerRoutePlatform()
        val controller = LoudspeakerRouteController(platform)

        controller.activate()
        controller.deactivate()
        controller.deactivate()
        controller.activate()

        assertEquals(2, platform.captureCount)
        assertEquals(2, platform.selectCount)
        assertEquals(1, platform.restoreCount)
    }

    @Test
    fun `failed selection can be retried without replacing the captured route`() {
        val platform = FakeLoudspeakerRoutePlatform(selectionResults = ArrayDeque(listOf(false, true)))
        val controller = LoudspeakerRouteController(platform)

        assertFalse(controller.activate())
        assertTrue(controller.activate())
        controller.deactivate()

        assertEquals(1, platform.captureCount)
        assertEquals(2, platform.selectCount)
        assertEquals(1, platform.restoreCount)
    }

    @Test
    fun `capture failure leaves the controller inactive`() {
        val platform = FakeLoudspeakerRoutePlatform(failCapture = true)
        val controller = LoudspeakerRouteController(platform)

        assertFalse(controller.activate())
        controller.deactivate()

        assertEquals(1, platform.captureCount)
        assertEquals(0, platform.selectCount)
        assertEquals(0, platform.restoreCount)
    }

    private class FakeLoudspeakerRoutePlatform(
        private val selectionResults: ArrayDeque<Boolean> = ArrayDeque(listOf(true)),
        private val failCapture: Boolean = false,
    ) : LoudspeakerRoutePlatform {
        var captureCount = 0
        var selectCount = 0
        var restoreCount = 0

        override fun captureCurrentRoute() {
            captureCount += 1
            if (failCapture) error("capture failed")
        }

        override fun selectLoudspeaker(): Boolean {
            selectCount += 1
            return if (selectionResults.size > 1) {
                selectionResults.removeFirst()
            } else {
                selectionResults.first()
            }
        }

        override fun restoreCapturedRoute() {
            restoreCount += 1
        }
    }
}
