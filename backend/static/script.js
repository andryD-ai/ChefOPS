let playing = false;
let totalFrames = 0;
let fps = 30;
let currentFrame = 0;
let timer = null;
let isSeeking = false;
const playback_speed = 1;  // 0.5 = 50% slower
let isChange = false;
let click = 0;
let previousUrl;

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function selectVideo(videoName) {
    if (isChange){return;}
    click = click +1 ;
    playing = false;
    isChange = true;
    if (timer) clearInterval(timer);
    
    try {
        await fetch('/load_video', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({video: videoName})
    });}
    catch (err) {
        console.error("Error in selectVideo():", err);
        alert("Failed to load video: " + err.message);
    } 

    // Wait for thread start and create few frame
    await sleep(1000);
    const info = await fetch('/video_info');
    const data = await info.json();
    totalFrames = data.total_frames;
    fps = data.fps;
    document.getElementById('timeline').max = totalFrames;
    currentFrame = 0;
    updateTimeDisplay();
    play();
    isChange = false;
}

function togglePlay() {
    playing = !playing;
    if (playing) {
        timer = setInterval(fetchFrame, (1000 / fps) / playback_speed);
    } else {
        clearInterval(timer);
    }
}

function play() {
    playing = true;
    timer = setInterval(fetchFrame, (1000 / fps) / playback_speed);
}

async function fetchFrame() {
    if (isSeeking) return; // prevent conflicting seek
    if (isChange) return;
    const res = await fetch('/get_frame', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({})
    });

    if (res.headers.get("content-type").includes("application/json")) {
        // clearInterval(timer);
        // playing = false;
        return;
    }
    
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    document.getElementById('videoFrame').src = url;
    if (previousUrl) URL.revokeObjectURL(previousUrl);
    previousUrl = url;
    if (!isSeeking){
        document.getElementById('timeline').value = ++currentFrame;
    }
    updateTimeDisplay();
}

// Preview only during slider movement (no server call)
function previewSeek() {
    isSeeking = true;
    let seekTo = parseInt(document.getElementById('timeline').value);
    displayTimeFromFrame(seekTo);
}

// Actual seek after mouse release
async function commitSeek() {
    clearInterval(timer);
    let seekTo = parseInt(document.getElementById('timeline').value);
    currentFrame = seekTo;
    const res = await fetch('/get_frame', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({seek: seekTo})
    });

    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    document.getElementById('videoFrame').src = url;
    document.getElementById('timeline').value = seekTo;
    if (previousUrl) URL.revokeObjectURL(previousUrl);
    previousUrl = url;
    updateTimeDisplay();
    isSeeking = false;
    playing = true;
    timer = setInterval(fetchFrame, (1000 / fps) / playback_speed);
    
}

function displayTimeFromFrame(frameNumber) {
    let seconds = frameNumber / fps;
    let hrs = Math.floor(seconds / 3600);
    let mins = Math.floor((seconds % 3600) / 60);
    let secs = Math.floor(seconds % 60);
    document.getElementById('currentTime').textContent = 
        `${hrs.toString().padStart(2,'0')}:${mins.toString().padStart(2,'0')}:${secs.toString().padStart(2,'0')}`;
}

function updateTimeDisplay() {
    displayTimeFromFrame(currentFrame);
}

async function submitErr() {
    const textbox = document.getElementById('errDescribe').value;

    try{
    const img = document.getElementById('videoFrame');
    const canvas = document.createElement('canvas');
    canvas.width = img.naturalWidth;
    canvas.height = img.naturalHeight;

    const ctx = canvas.getContext('2d');
    ctx.drawImage(img, 0, 0);

    // Get base64 string of image
    const base64Image = canvas.toDataURL('image/jpeg');

    const base64Data = base64Image.split(',')[1]; // Remove the data URL header

    // Send to backend via POST
    await fetch('/submit_button', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        userId: 1,
        currentFrame: currentFrame,
        err: textbox,
        image: base64Data})
    });
    }
    catch (err) {
        console.error("Error in selectVideo():", err);
        alert("Failed to load video: " + err.message);
    } 
}
alert("Failed to load video: " + err.message);