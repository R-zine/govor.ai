package ai.govor.core

/**
 * Tracks whether a foreground transition should restore a user-requested session.
 *
 * Android lifecycle callbacks remain outside this pure policy so the reconnect decision can be
 * tested without an Android runtime. An explicit disconnect always wins over a later foreground.
 */
class LifecycleReconnectPolicy {
    private var connectionRequested = false
    private var backgroundedWhileConnected = false

    fun connectionRequested() {
        connectionRequested = true
    }

    fun explicitDisconnect() {
        connectionRequested = false
        backgroundedWhileConnected = false
    }

    fun enterBackground(): Boolean {
        backgroundedWhileConnected = connectionRequested
        return backgroundedWhileConnected
    }

    fun enterForeground(): Boolean {
        val reconnect = connectionRequested && backgroundedWhileConnected
        backgroundedWhileConnected = false
        return reconnect
    }

    fun shouldRetryConnection(): Boolean = connectionRequested && !backgroundedWhileConnected
}
