package ai.govor.core

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertThrows
import org.junit.jupiter.api.Test

class SpeechTimelineTest {
    private val alignment = listOf(
        WordAlignmentPayload(0, 0, 400_000),
        WordAlignmentPayload(1, 500_000, 900_000),
    )

    @Test
    fun `highlight uses provider media time and preserves gaps`() {
        assertEquals(0, SpeechTimeline.activeWord(399_999, alignment))
        assertNull(SpeechTimeline.activeWord(450_000, alignment))
        assertEquals(1, SpeechTimeline.activeWord(500_000, alignment))
        assertNull(SpeechTimeline.activeWord(900_000, alignment))
        assertNull(SpeechTimeline.activeWord(100_000, null))
    }

    @Test
    fun `wall duration follows supported playback rate`() {
        assertEquals(2_000_000, SpeechTimeline.wallDurationUs(1_500_000, 0.75f))
        assertEquals(1_500_000, SpeechTimeline.wallDurationUs(1_500_000, 1.0f))
        assertEquals(1_200_000, SpeechTimeline.wallDurationUs(1_500_000, 1.25f))
        assertThrows(IllegalArgumentException::class.java) {
            SpeechTimeline.wallDurationUs(1_000_000, 2.0f)
        }
    }
}
