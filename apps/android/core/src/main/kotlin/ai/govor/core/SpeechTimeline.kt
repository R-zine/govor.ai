package ai.govor.core

/** Pure media-time helpers shared by playback and deterministic JVM tests. */
object SpeechTimeline {
    val supportedRates = listOf(0.75f, 1.0f, 1.25f)

    fun activeWord(mediaTimeUs: Long, alignment: List<WordAlignmentPayload>?): Int? =
        alignment?.firstOrNull { mediaTimeUs >= it.start_us && mediaTimeUs < it.end_us }?.word_index

    fun wallDurationUs(mediaDurationUs: Long, playbackRate: Float): Long {
        require(playbackRate in supportedRates)
        return (mediaDurationUs / playbackRate).toLong()
    }
}
