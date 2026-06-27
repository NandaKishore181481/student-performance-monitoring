import os
import asyncio
import edge_tts

async def _tts_task(text: str, voice: str, file_path: str):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(file_path)

def generate_voice_file(text: str, file_path: str, voice: str = "en-US-GuyNeural") -> bool:
    """
    Synchronously compiles text to speech and saves it as an MP3 file at file_path.
    Handles existing running event loops gracefully by spawning a new thread.
    """
    if not text:
        print("Empty text provided for TTS generation.")
        return False

    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Spawn in a separate thread if an event loop is already running in the current thread
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                import threading
                success = False
                def run_in_thread():
                    nonlocal success
                    try:
                        asyncio.run(_tts_task(text, voice, file_path))
                        success = True
                    except Exception as thread_ex:
                        print(f"TTS Thread compilation failed: {thread_ex}")
                
                t = threading.Thread(target=run_in_thread)
                t.start()
                t.join()
                return success
        except RuntimeError:
            # No running event loop in the current thread, run directly
            asyncio.run(_tts_task(text, voice, file_path))
            return True
            
        return True
    except Exception as e:
        print(f"Failed to generate Edge-TTS voice: {e}")
        return False

if __name__ == "__main__":
    # Test generation
    test_path = os.path.join("data", "announcements", "test_announcement.mp3")
    res = generate_voice_file("Attention all students. This is a voice test from the EduInsight AI alert system.", test_path)
    print(f"Test Generation Successful: {res} | Output path: {test_path}")
