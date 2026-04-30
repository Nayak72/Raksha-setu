package com.raksha.setu

import android.content.Context
import java.util.UUID

/** Generates and persists a stable device UUID using SharedPreferences. */
object DeviceIdentifier {
    private const val PREFS = "raksha_setu_prefs"
    private const val KEY = "device_id"

    fun getDeviceId(context: Context): String {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        var id = prefs.getString(KEY, null)
        if (id == null) {
            id = UUID.randomUUID().toString()
            prefs.edit().putString(KEY, id).apply()
        }
        return id
    }
}
