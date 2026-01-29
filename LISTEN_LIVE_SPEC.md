# Listen Live Feature Specification

## Overview
Add a "Listen Live" feature to the Stream Checker web interface that allows users to listen to audio streams directly in their browser without leaving the page.

## User Interface

### Layout
```
┌─────────────────────────────────────────┐
│  Stream Checker                         │
│  [Stream URL Input Field]               │
│                                         │
│  ┌───────────────────────────────────┐ │
│  │  Listen Live                      │ │
│  │  [▶ Play] [⏸ Pause] [⏹ Stop]    │ │
│  │  [Volume Slider] [Mute]          │ │
│  │  [Time Display]                  │ │
│  └───────────────────────────────────┘ │
│                                         │
│  ┌───────────────────────────────────┐ │
│  │  Check Stream                     │ │
│  │  [Test Options Checkboxes]       │ │
│  │  [Check Stream Button]           │ │
│  └───────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

### Components
1. **Stream URL Input** (existing, at top)
2. **Listen Live Section** (new, below URL input)
   - Play/Pause/Stop controls
   - Volume control slider
   - Mute button
   - Current time / duration display
   - Status indicator (Loading, Playing, Paused, Error)
3. **Check Stream Section** (existing, below Listen Live)

## Technical Approach

### Recommended: Browser-Native HTML5 Audio Player

**Why Browser-Native:**
- ✅ No external dependencies (VLC, plugins, etc.)
- ✅ Works across all modern browsers (Chrome, Firefox, Safari, Edge)
- ✅ Simple implementation - just HTML5 `<audio>` element
- ✅ No backend changes required
- ✅ Mobile-friendly (works on iOS/Android)
- ✅ Low latency, direct stream connection
- ✅ Built-in browser controls and error handling

**Implementation:**
- Use HTML5 `<audio>` element with `controls` attribute (or custom controls)
- JavaScript API: `HTMLAudioElement` for programmatic control
- Direct stream URL connection (no proxy needed)
- Handle CORS if needed (most streams support CORS)

### Alternative Approaches (Not Recommended)

**VLC Integration:**
- ❌ VLC Web Plugin is deprecated
- ❌ VLC.js requires WebAssembly and has limitations
- ❌ Adds complexity and dependencies
- ❌ May not work on all browsers/devices

**Backend Streaming Proxy:**
- ❌ Adds server load and bandwidth costs
- ❌ Increases latency
- ❌ Requires backend changes
- ❌ More complex to implement

## Implementation Details

### HTML Structure
```html
<section class="listen-live-section">
    <h2>Listen Live</h2>
    <div class="audio-player">
        <audio id="streamPlayer" preload="none">
            Your browser does not support the audio element.
        </audio>
        <div class="player-controls">
            <button id="playBtn">▶ Play</button>
            <button id="pauseBtn" style="display:none;">⏸ Pause</button>
            <button id="stopBtn">⏹ Stop</button>
            <input type="range" id="volumeSlider" min="0" max="1" step="0.1" value="1">
            <button id="muteBtn">🔊</button>
            <span id="timeDisplay">--:--</span>
            <span id="playerStatus">Ready</span>
        </div>
    </div>
</section>
```

### JavaScript Functionality

**Core Features:**
1. **Play/Pause/Stop Controls**
   - Play: Set audio source to stream URL, call `play()`
   - Pause: Call `pause()`
   - Stop: Call `pause()` and reset `currentTime` to 0

2. **Volume Control**
   - Slider: Update `audio.volume` (0.0 to 1.0)
   - Mute: Toggle `audio.muted` property

3. **Time Display**
   - Show current playback time
   - For live streams, show "LIVE" or elapsed time
   - Update every second using `timeupdate` event

4. **Status Management**
   - Loading: When `loadstart` event fires
   - Playing: When `playing` event fires
   - Paused: When `pause` event fires
   - Error: When `error` event fires (show error message)

5. **Error Handling**
   - Network errors (connection failed)
   - Format errors (unsupported codec)
   - CORS errors (if stream doesn't allow cross-origin)
   - Display user-friendly error messages

### CSS Styling
- Match existing dark theme
- Responsive design for mobile
- Visual feedback for button states
- Smooth transitions for controls

## User Experience Flow

1. User enters stream URL
2. User clicks "Play" button
3. Audio player loads stream (shows "Loading...")
4. Stream starts playing (shows "Playing")
5. User can:
   - Pause/Resume playback
   - Adjust volume
   - Stop playback
   - Check stream while listening (separate feature)

## Edge Cases & Considerations

### CORS Issues
- Some streams may block cross-origin requests
- Solution: Display helpful error message
- Future: Could add backend proxy as fallback (optional)

### Stream Format Support
- MP3 streams: ✅ Supported (all browsers)
- AAC streams: ✅ Supported (all browsers)
- HLS streams (.m3u8): 
  - ✅ Safari (macOS/iOS): Native support
  - ✅ Chrome Desktop (v142+, Dec 2024+): Native support
  - ⚠️ Firefox/Edge: Requires HLS.js library (recommended fallback)
  - ⚠️ Older Chrome versions: Requires HLS.js library
- Icecast/Shoutcast: ✅ Supported (all browsers)

**Note on HLS**: Chrome recently added native HLS support, but for maximum compatibility across all browsers and versions, consider using HLS.js as a fallback. It's lightweight (~100KB) and provides consistent HLS playback across all browsers.

### Mobile Considerations
- iOS Safari requires user interaction to start audio
- Use button click handler (not auto-play)
- Test on actual devices

### Browser Compatibility
- Modern browsers: Full support
- Older browsers: Graceful degradation
- Fallback message if audio element not supported

## Future Enhancements (Optional)

1. **Playlist Support**: Queue multiple streams
2. **Recording**: Save stream to file (requires backend)
3. **Visualizer**: Audio waveform visualization
4. **Stream Info Display**: Show current track info from metadata
5. **Presets**: Save favorite streams
6. **Keyboard Shortcuts**: Spacebar for play/pause, etc.

## Implementation Steps

1. **Phase 1: Basic Player** (MVP)
   - Add HTML5 audio element
   - Implement Play/Pause/Stop buttons
   - Add volume control
   - Basic error handling

2. **Phase 2: Polish**
   - Add time display
   - Improve error messages
   - Add loading states
   - Style to match dark theme

3. **Phase 3: Advanced** (Optional)
   - HLS.js fallback for Firefox/Edge/Older Chrome
   - Stream metadata display
   - Keyboard shortcuts

## Files to Modify

- `frontend/index.html`: Add Listen Live section
- `frontend/app.js`: Add audio player JavaScript logic
- `frontend/style.css`: Style audio player controls

## Testing Checklist

- [ ] Play MP3 stream
- [ ] Play AAC stream
- [ ] Play HLS stream (if supported)
- [ ] Pause/Resume functionality
- [ ] Stop functionality
- [ ] Volume control
- [ ] Mute functionality
- [ ] Error handling (invalid URL, network error)
- [ ] Mobile browser testing (iOS Safari, Android Chrome)
- [ ] CORS error handling
- [ ] Visual feedback for all states

## Conclusion

**Recommended Approach: Browser-Native HTML5 Audio Player**

This is the simplest, most reliable, and most user-friendly solution. No new project needed - just add the feature to the existing web frontend. The HTML5 audio element handles all the complexity of streaming, codec support, and browser compatibility.

**No Backend Changes Required**: The audio player connects directly to the stream URL from the browser, so no API changes or new endpoints are needed.
