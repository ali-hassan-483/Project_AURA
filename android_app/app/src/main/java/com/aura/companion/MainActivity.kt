package com.aura.companion

import android.media.MediaPlayer
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.EditText
import android.widget.ImageButton
import android.widget.ImageView
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.bumptech.glide.Glide
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {

    private lateinit var recyclerView: RecyclerView
    private lateinit var messageInput: EditText
    private lateinit var btnSend: ImageButton
    private lateinit var btnSettings: ImageButton
    private lateinit var adapter: ChatAdapter
    private val messages = mutableListOf<ChatMessage>()
    private val apiClient = AuraApiClient()
    private var mediaPlayer: MediaPlayer? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        recyclerView = findViewById(R.id.chatRecyclerView)
        messageInput = findViewById(R.id.messageInput)
        btnSend = findViewById(R.id.btnSend)
        btnSettings = findViewById(R.id.btnSettings)

        adapter = ChatAdapter(messages) { audioUrl ->
            playAudio(audioUrl)
        }
        recyclerView.layoutManager = LinearLayoutManager(this).apply {
            stackFromEnd = true
        }
        recyclerView.adapter = adapter

        // Welcome message
        messages.add(
            ChatMessage(
                sender = "aura",
                text = "Assalam-o-Alaikum meri jaan! ❤️ Main Aura hoon. Aaj ka din kaisa guzra aapka?"
            )
        )
        adapter.notifyItemInserted(0)

        btnSend.setOnClickListener {
            val text = messageInput.text.toString().trim()
            if (text.isNotEmpty()) {
                sendMessage(text)
            }
        }

        btnSettings.setOnClickListener {
            showServerSettingsDialog()
        }
    }

    private fun sendMessage(text: String) {
        val userMsg = ChatMessage(sender = "user", text = text)
        messages.add(userMsg)
        adapter.notifyItemInserted(messages.size - 1)
        recyclerView.scrollToPosition(messages.size - 1)
        messageInput.setText("")

        lifecycleScope.launch {
            val result = apiClient.sendMessage("+923001234567", text)
            result.onSuccess { response ->
                val auraMsg = ChatMessage(
                    sender = "aura",
                    text = response.reply,
                    imageUrl = response.imageUrl,
                    audioUrl = response.voiceUrl
                )
                messages.add(auraMsg)
                adapter.notifyItemInserted(messages.size - 1)
                recyclerView.scrollToPosition(messages.size - 1)

                // Auto-play voice note if returned
                response.voiceUrl?.let { playAudio(it) }
            }.onFailure { err ->
                Toast.makeText(this@MainActivity, "Connection error: ${err.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun playAudio(url: String) {
        try {
            mediaPlayer?.release()
            mediaPlayer = MediaPlayer().apply {
                setDataSource(url)
                prepareAsync()
                setOnPreparedListener { start() }
            }
        } catch (e: Exception) {
            Toast.makeText(this, "Could not play voice note: ${e.message}", Toast.LENGTH_SHORT).show()
        }
    }

    private fun showServerSettingsDialog() {
        val input = EditText(this).apply {
            hint = "http://YOUR_SERVER_IP:8000"
        }
        AlertDialog.Builder(this)
            .setTitle("Project AURA Server URL")
            .setMessage("Enter the IP or domain where Project AURA is hosted:")
            .setView(input)
            .setPositiveButton("Save") { _, _ ->
                val url = input.text.toString().trim()
                if (url.isNotEmpty()) {
                    apiClient.updateBaseUrl(url)
                    Toast.makeText(this, "Server URL updated!", Toast.LENGTH_SHORT).show()
                }
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    override fun onDestroy() {
        super.onDestroy()
        mediaPlayer?.release()
    }
}

class ChatAdapter(
    private val list: List<ChatMessage>,
    private val onAudioClick: (String) -> Unit
) : RecyclerView.Adapter<ChatAdapter.ChatViewHolder>() {

    class ChatViewHolder(val view: View) : RecyclerView.ViewHolder(view) {
        val textMessage: TextView? = view.findViewById(R.id.textMessage)
        val imageAttachment: ImageView? = view.findViewById(R.id.imageAttachment)
        val btnPlayAudio: View? = view.findViewById(R.id.btnPlayAudio)
    }

    override fun getItemViewType(position: Int): Int {
        return if (list[position].sender == "user") 1 else 0
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ChatViewHolder {
        val layout = if (viewType == 1) {
            android.R.layout.simple_list_item_1
        } else {
            android.R.layout.simple_list_item_2
        }
        val v = LayoutInflater.from(parent.context).inflate(layout, parent, false)
        return ChatViewHolder(v)
    }

    override fun onBindViewHolder(holder: ChatViewHolder, position: Int) {
        val msg = list[position]
        holder.view.findViewById<TextView>(android.R.id.text1)?.apply {
            text = msg.text
            setTextColor(android.graphics.Color.WHITE)
        }
    }

    override fun getItemCount(): Int = list.size
}
