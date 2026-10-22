package ai.govor.core

import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

class LifecycleReconnectPolicyTest {
    @Test
    fun `requested connection reconnects once after background`() {
        val policy = LifecycleReconnectPolicy()

        policy.connectionRequested()

        assertTrue(policy.enterBackground())
        assertTrue(policy.enterForeground())
        assertFalse(policy.enterForeground())
    }

    @Test
    fun `explicit disconnect suppresses foreground reconnect`() {
        val policy = LifecycleReconnectPolicy()

        policy.connectionRequested()
        assertTrue(policy.enterBackground())
        policy.explicitDisconnect()

        assertFalse(policy.enterForeground())
    }

    @Test
    fun `unused policy does not pause or reconnect`() {
        val policy = LifecycleReconnectPolicy()

        assertFalse(policy.enterBackground())
        assertFalse(policy.enterForeground())
        assertFalse(policy.shouldRetryConnection())
    }

    @Test
    fun `requested foreground connection can retry after network recovery`() {
        val policy = LifecycleReconnectPolicy()

        policy.connectionRequested()
        assertTrue(policy.shouldRetryConnection())

        policy.enterBackground()
        assertFalse(policy.shouldRetryConnection())

        policy.enterForeground()
        assertTrue(policy.shouldRetryConnection())
    }
}
