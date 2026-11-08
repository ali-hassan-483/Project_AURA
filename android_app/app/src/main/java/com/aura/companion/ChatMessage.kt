package com.aura.companion

data class ChatMessage(
    val id: String = java.util.UUID.randomUUID().toString(),
    val sender: String, // "user" or "aura"
    val text: String,
    val imageUrl: String? = null,
    val audioUrl: String? = null,
    val timestamp: Long = System.currentTimeMillis()
)
