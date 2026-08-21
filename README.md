An app for transcribing audio/video to text. Written for educational purposes to learn how to integrate LLMs into the backend.

The LLM might hallucinate because of the sound quality. Working on this.

You can try it out via link: [hackHackXanum-audio-transcription.hf.space](https://hackHackXanum-audio-transcription.hf.space).

## Architecture

### Observability & Logging

Application logs are emitted directly to stdout/stderr as an event stream, adhering to Twelve-Factor App principles (Factor XI: Logs).
The containerized app does not manage log storage internally. When deployed on Hugging Face Spaces, HF automatically captures, aggregates, and renders these stdout streams in the runtime logs console.