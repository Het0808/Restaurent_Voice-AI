const $ = (id) => document.getElementById(id);
let socket, stream, context, source, processor, playing = [], active = false;
const log = (value) => { $('events').textContent += `${typeof value === 'string' ? value : JSON.stringify(value)}\n`; };
const control = (type) => socket?.readyState === WebSocket.OPEN && socket.send(JSON.stringify({type}));

function resample(input, fromRate, toRate) {
  const output = new Int16Array(Math.floor(input.length * toRate / fromRate));
  for (let i = 0; i < output.length; i++) {
    const value = Math.max(-1, Math.min(1, input[Math.floor(i * fromRate / toRate)]));
    output[i] = value < 0 ? value * 32768 : value * 32767;
  }
  return output.buffer;
}

async function playPcm(buffer) {
  const samples = new Int16Array(buffer), audio = new Float32Array(samples.length);
  for (let i = 0; i < samples.length; i++) audio[i] = samples[i] / 32768;
  const audioBuffer = context.createBuffer(1, audio.length, 24000);
  audioBuffer.copyToChannel(audio, 0); const node = context.createBufferSource();
  node.buffer = audioBuffer; node.connect(context.destination); node.start(); playing.push(node);
}

$('connect').onclick = () => {
  if (socket?.readyState === WebSocket.OPEN) { control('session.end'); return; }
  socket = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/api/v1/voice/ws`);
  socket.binaryType = 'arraybuffer';
  socket.onopen = () => socket.send(JSON.stringify({type:'session.start', protocol_version:'1.0', language:$('language').value, audio:{format:'pcm_s16le', sample_rate:16000, channels:1, frame_duration_ms:20}}));
  socket.onmessage = (event) => {
    if (event.data instanceof ArrayBuffer) { playPcm(event.data); return; }
    const data = JSON.parse(event.data); log(data);
    if (data.type === 'session.ready') { $('session').textContent=data.session_id; $('conversation').textContent=data.conversation_id; ['mic','interrupt','reset'].forEach(id => $(id).disabled=false); }
    if (data.type === 'transcript.final') $('transcript').textContent += `${data.text}\n`;
    if (data.type === 'assistant.text') $('assistant').textContent += `${data.text}\n`;
    if (data.type === 'assistant.audio.end' && data.interrupted) { playing.forEach(node => { try { node.stop(); } catch {} }); playing=[]; }
  };
  socket.onclose = () => { log('disconnected'); $('mic').disabled=true; active=false; };
};

$('mic').onclick = async () => {
  if (active) { processor.disconnect(); source.disconnect(); stream.getTracks().forEach(t=>t.stop()); control('audio.commit'); active=false; $('mic').textContent='Start microphone'; return; }
  context ||= new AudioContext(); stream = await navigator.mediaDevices.getUserMedia({audio:{channelCount:1}});
  source=context.createMediaStreamSource(stream); processor=context.createScriptProcessor(1024,1,1);
  processor.onaudioprocess=(event)=>socket.send(resample(event.inputBuffer.getChannelData(0), context.sampleRate, 16000));
  source.connect(processor); processor.connect(context.destination); active=true; $('mic').textContent='Stop microphone';
};
$('interrupt').onclick = () => control('assistant.interrupt');
$('reset').onclick = () => control('conversation.reset');
