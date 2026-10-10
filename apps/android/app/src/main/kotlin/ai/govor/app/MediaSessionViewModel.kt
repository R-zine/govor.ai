package ai.govor.app

import android.app.Application
import androidx.lifecycle.AndroidViewModel

class MediaSessionViewModel(application: Application) : AndroidViewModel(application) {
    val session = WebRtcSession(application.applicationContext)
    val lesson = LessonSessionClient()

    fun connect(mediaHost: String, controlHost: String, pairingToken: String) {
        session.connect(mediaHost, pairingToken)
        lesson.connect(controlHost)
    }

    fun setPushToTalk(active: Boolean) {
        session.setPushToTalk(active)
        if (active) lesson.beginRecording() else lesson.submitRecording()
    }

    fun disconnect() {
        lesson.disconnect()
        session.disconnect()
    }

    override fun onCleared() {
        lesson.release()
        session.release()
    }
}
