# Stream Checker Web Interface Redesign Specification

## Overview

This specification outlines three major enhancements to the Stream Checker web interface:
1. **Dark Mode Technical Dashboard Redesign** - A data-rich, professional monitoring interface inspired by Datadog
2. **Test Component Selection UI** - Replace phase-based selection with user-friendly checkboxes for selecting test components
3. **Test Results History Page** - A comprehensive list view of all test results from the database

### Key Principle: User-Focused Language
- **Remove all "phase" terminology** - This was internal development language, not meaningful to end users
- **Use descriptive test component names** - Users select what they want to test, not development phases
- **Clear, actionable labels** - Each checkbox clearly describes what will be tested

---

## Part 1: Test Component Selection UI (Replaces Phase Selection)

### Overview
Replace the phase-based dropdown with a user-friendly checkbox interface that lets users select which test components they want to run. Remove all "phase" terminology from the user interface.

### Checkbox Options

**Test Components:**
1. **☑ Basic Connectivity**
   - HTTP/HTTPS connection test
   - SSL/TLS certificate validation
   - Response time measurement
   - Server headers analysis
   - *Icon: 🔗 Link/Network*

2. **☑ Stream Information**
   - Stream parameters (bitrate, codec, sample rate, channels)
   - Stream type detection (Icecast, Shoutcast, HLS, etc.)
   - Container format
   - *Icon: 📊 Chart/Data*

3. **☑ Metadata**
   - Stream title, genre, artist
   - Station information
   - Description
   - ICY metadata (if available)
   - *Icon: 🏷️ Tag/Label*

4. **☑ Player Compatibility**
   - VLC player connectivity test
   - Format compatibility check
   - Buffering analysis
   - Connection quality metrics
   - *Icon: ▶️ Play/Media*

5. **☑ Audio Quality**
   - Silence detection
   - Error message detection
   - Audio quality metrics (volume, dynamic range)
   - Clipping detection
   - *Icon: 🎵 Music/Audio*

6. **☑ Ad Detection**
   - Ad marker detection
   - Ad break duration tracking
   - Ad frequency analysis
   - *Icon: 📢 Broadcast/Ad*

### UI Design

**Layout:**
```
┌─────────────────────────────────────────────────┐
│  Select Tests to Run                           │
├─────────────────────────────────────────────────┤
│  ☑ Basic Connectivity          🔗              │
│     HTTP connection, SSL certificate, timing    │
│                                                 │
│  ☑ Stream Information          📊              │
│     Bitrate, codec, sample rate, stream type    │
│                                                 │
│  ☑ Metadata                    🏷️              │
│     Title, genre, artist, description           │
│                                                 │
│  ☑ Player Compatibility        ▶️              │
│     VLC connectivity, format support            │
│                                                 │
│  ☑ Audio Quality               🎵              │
│     Silence detection, error messages, metrics │
│                                                 │
│  ☑ Ad Detection                📢              │
│     Ad markers, break tracking                 │
│                                                 │
│  [Select All] [Deselect All]                   │
└─────────────────────────────────────────────────┘
```

**Features:**
- **Default State**: All checkboxes checked (full test)
- **Validation**: At least one test must be selected
- **Dependency**: "Basic Connectivity" auto-selected if any other test is selected
- **Tooltips**: Hover to see detailed description of each test
- **Quick Actions**: "Select All" / "Deselect All" buttons
- **Visual Feedback**: Icons and brief descriptions for each option

**Styling:**
- Dark theme checkboxes with accent color when checked
- Subtle hover effects
- Clear visual hierarchy
- Responsive grid layout (2 columns on desktop, 1 on mobile)

### API Request Format

**Old Format (to be removed):**
```json
{
  "url": "https://example.com/stream.mp3",
  "phase": 4
}
```

**New Format:**
```json
{
  "url": "https://example.com/stream.mp3",
  "tests": {
    "connectivity": true,
    "stream_info": true,
    "metadata": true,
    "player_test": false,
    "audio_analysis": true,
    "ad_detection": false
  }
}
```

### Backend Mapping

The backend maps checkbox selections to internal phase logic:

- `connectivity: true` → Run Phase 1 (connectivity, SSL, headers)
- `stream_info: true` → Run Phase 1 (parameters, stream type)
- `metadata: true` → Run Phase 1 (metadata extraction)
- `player_test: true` → Run Phase 2
- `audio_analysis: true` → Run Phase 3
- `ad_detection: true` → Run Phase 4

**Note**: The backend still uses phases internally, but this is hidden from users.

### Response Format

**Remove from response:**
- `"phase": 4` field

**Add to response:**
- `"tests_completed": ["connectivity", "stream_info", "player_test", ...]` - Array of completed tests
- `"tests_requested": ["connectivity", "stream_info", ...]` - Array of requested tests

---

## Part 2: Dark Mode Technical Dashboard Redesign

### Design Goals

- **Professional Monitoring Aesthetic**: Inspired by Datadog's technical dashboard style
- **Data-Rich Presentation**: Emphasize metrics, charts, and technical details
- **Dark Mode Theme**: Modern dark color scheme optimized for extended viewing
- **Improved Information Density**: Show more data without overwhelming the user
- **Technical Focus**: Appeal to technical users (stream operators, engineers)

### Color Scheme

**Primary Colors:**
- **Background**: `#0a0e27` (very dark blue-gray, similar to Datadog)
- **Card Background**: `#161b33` (slightly lighter dark blue)
- **Border**: `#2a3458` (subtle blue-gray border)
- **Text Primary**: `#ffffff` (white)
- **Text Secondary**: `#b4b8c8` (light gray)
- **Text Muted**: `#6b7280` (medium gray)

**Accent Colors:**
- **Success/Healthy**: `#00d97e` (bright green)
- **Warning**: `#ff9800` (orange)
- **Error/Critical**: `#ff4444` (red)
- **Info**: `#5b8def` (blue)
- **Primary Action**: `#7c3aed` (purple)

**Status Indicators:**
- **Health Score 90-100**: `#00d97e` (green)
- **Health Score 70-89**: `#ffc107` (yellow)
- **Health Score 50-69**: `#ff9800` (orange)
- **Health Score 0-49**: `#ff4444` (red)

### Layout Changes

#### Header Section
- **Dark background** with subtle gradient
- **Logo/branding** on left
- **Stream URL input** with dark theme styling
- **Test button** with prominent accent color
- **Navigation links** (Home, Test History)

#### Test Component Selection Section
- **Checkbox grid** (see Part 1 for details)
- **Dark theme styling** matching overall design
- **Integrated into main form** (not separate section)

#### Results Display

**Card-Based Layout:**
- Each result section in a **dark card** with subtle border
- **Card shadows** for depth (subtle, not heavy)
- **Hover effects** for interactivity
- **Collapsible sections** for detailed information

**Metrics Display:**
- **Large, prominent numbers** for key metrics (health score, response time, bitrate)
- **Mini charts/sparklines** for trends (if historical data available)
- **Status badges** with color coding
- **Progress bars** for percentages (silence, buffering, etc.)

**Information Hierarchy:**
1. **Health Score** - Large, prominent display at top
2. **Quick Stats** - Key metrics in a grid (response time, bitrate, status)
3. **Detailed Sections** - Expandable/collapsible cards for each phase
4. **Raw Data** - Technical details in code-style blocks

### Typography

- **Headings**: Bold, slightly larger, high contrast
- **Body Text**: Medium weight, readable gray
- **Code/Metrics**: Monospace font for technical data
- **Labels**: Small, uppercase, muted color

### Component Redesigns

#### Health Score Display
```
┌─────────────────────────────────┐
│  Health Score                   │
│  ┌───────────────────────────┐  │
│  │     85 / 100              │  │
│  │  ████████████░░░░░░░░    │  │
│  │  ⚠ Good                   │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```

#### Metrics Grid
- **4-column grid** showing:
  - Response Time (ms)
  - Bitrate (kbps)
  - Stream Type
  - Status
- Each metric in a **small card** with icon
- **Color-coded** based on value ranges

#### Phase Results Cards
- **Collapsible sections** for each phase
- **Expand icon** to show/hide details
- **Status indicator** (✓/⚠/✗) with color
- **Technical details** in expandable sections
- **Code blocks** for raw data (JSON, headers, etc.)

#### Stream Parameters Display
- **Table format** with dark theme
- **Alternating row colors** for readability
- **Highlight important values** (bitrate, codec)
- **Icons** for each parameter type

### Interactive Elements

- **Hover states**: Subtle highlight on cards
- **Click to expand**: Detailed information on demand
- **Smooth transitions**: Animated expand/collapse
- **Loading states**: Skeleton screens or spinners
- **Error states**: Clear, actionable error messages

### Responsive Design

- **Desktop**: Full multi-column layout
- **Tablet**: 2-column layout
- **Mobile**: Single column, stacked cards

---

## Part 2: Test Results History Page

### Overview

A new page (`/history` or `/results`) that displays all test results from the database in a table/list format.

### Database Query Requirements

**API Endpoint**: `GET /api/results` or `GET /api/test-runs`

**Query Parameters:**
- `limit` (optional): Number of results to return (default: 100)
- `offset` (optional): Pagination offset (default: 0)
- `stream_id` (optional): Filter by specific stream
- `sort` (optional): Sort field (default: `timestamp DESC`)
- `status` (optional): Filter by status (success, error, etc.)

**Database Methods Needed:**
- `get_all_test_runs(limit, offset, filters)` - Retrieve all test runs
- `get_test_run_count(filters)` - Get total count for pagination
- `get_test_run_by_id(test_run_id)` - Get single test run details

### Table Columns

**Required Columns (always visible):**
1. **Test ID** (`test_run_id`)
   - Format: First 8 characters of UUID (e.g., `550e8400`)
   - Clickable link to detailed view
   - Monospace font

2. **Stream URL** (`stream_url`)
   - Truncated if too long (show first 50 chars + "...")
   - Full URL on hover/tooltip
   - Clickable to test again

3. **Timestamp** (`timestamp`)
   - Format: `YYYY-MM-DD HH:MM:SS UTC`
   - Relative time option: "2 hours ago"

4. **Health Score** (`health_score`)
   - Large number display
   - Color-coded background
   - Progress bar indicator

5. **Status** (`overall_status`)
   - Badge with icon
   - Color-coded (green/yellow/red)

**Optional Columns (toggleable):**
6. **Response Time** (`connectivity.response_time_ms`)
   - Format: `245 ms`
   - Color-coded (green < 500ms, yellow < 1000ms, red >= 1000ms)

7. **Bitrate** (`stream_parameters.bitrate_kbps`)
   - Format: `128 kbps`
   - Show "N/A" if not available

8. **Stream Type** (`stream_type.type`)
   - Badge format
   - Color-coded by type

9. **Codec** (`stream_parameters.codec`)
   - Format: `MP3`, `AAC`, etc.

10. **Tests Completed** (`tests_completed`)
    - Format: `5/6` (tests completed / tests selected)
    - Icon indicator showing which components were tested
    - Tooltip showing list of completed tests

11. **Errors** (`error_count`)
    - Number of errors detected
    - Red badge if > 0

### Table Features

**Sorting:**
- Click column header to sort
- Sort indicators (↑/↓)
- Multi-column sorting (shift-click)

**Filtering:**
- **Search box**: Filter by stream URL or test ID
- **Status filter**: Dropdown (All, Success, Warning, Error)
- **Date range**: Date picker for time range
- **Stream type filter**: Dropdown (All, Icecast, Shoutcast, HLS, etc.)

**Pagination:**
- Page size selector (25, 50, 100, 200)
- Previous/Next buttons
- Page number display
- Total count display

**Row Actions:**
- **View Details**: Expand row or navigate to detail page
- **Re-test**: Quick action to test the same stream again
- **Copy Test ID**: Copy to clipboard
- **Export**: Download as CSV/JSON

### Detail View (Modal or Separate Page)

When clicking a test ID or "View Details":
- **Full test results** in expandable sections
- **All phases** with complete data
- **Raw JSON** view (toggleable)
- **Timeline** of test execution
- **Related tests** for same stream

### Page Layout

```
┌─────────────────────────────────────────────────────────┐
│  Test Results History                    [Filters] [Export] │
├─────────────────────────────────────────────────────────┤
│  Search: [____________]  Status: [All ▼]  Type: [All ▼] │
├─────────────────────────────────────────────────────────┤
│  Test ID  │ Stream URL        │ Time      │ Score │ Status │
├─────────────────────────────────────────────────────────┤
│  550e8400 │ example.com/...   │ 2h ago    │  85   │  ⚠     │
│  a1b2c3d4 │ stream2.com/...    │ 5h ago    │  92   │  ✓     │
│  ...      │ ...               │ ...       │ ...   │  ...   │
└─────────────────────────────────────────────────────────┘
│  Showing 1-25 of 150 results  [< Prev] [Next >]        │
└─────────────────────────────────────────────────────────┘
```

### API Implementation

**New Endpoint**: `GET /api/test-runs`

**Request:**
```http
GET /api/test-runs?limit=25&offset=0&sort=timestamp&order=desc
```

**Response:**
```json
{
  "test_runs": [
    {
      "test_run_id": "550e8400-e29b-41d4-a716-446655440000",
      "stream_id": "a1b2c3d4e5f6g7h8",
      "stream_url": "https://example.com/stream.mp3",
      "timestamp": "2026-01-25T21:12:13Z",
      "tests_completed": ["connectivity", "stream_info", "player_test", "audio_analysis", "ad_detection"],
      "health_score": 85,
      "status": "warning",
      "connectivity": {
        "status": "success",
        "response_time_ms": 245
      },
      "stream_parameters": {
        "bitrate_kbps": 128,
        "codec": "MP3"
      },
      "stream_type": {
        "type": "Icecast"
      }
    }
  ],
  "total": 150,
  "limit": 25,
  "offset": 0
}
```

### Database Schema Considerations

**Required Fields in Response:**
- All fields from `test_runs` table
- Aggregated data from `results` JSON column
- Calculated fields (health_score, status, error_count)

**Performance:**
- **Indexes**: Ensure indexes on `timestamp`, `stream_id`, `test_run_id`
- **Pagination**: Use LIMIT/OFFSET or cursor-based pagination
- **Caching**: Consider caching recent results (last 100)

---

## Implementation Phases

### Phase 1: Dark Mode Redesign & Test Selection UI
1. Update CSS with dark theme colors
2. Redesign main dashboard layout
3. Replace phase dropdown with checkbox selection UI
4. Update API to accept test component selection instead of phase numbers
5. Update component styles (cards, badges, metrics)
6. Add collapsible sections
7. Improve typography and spacing
8. Test responsive design

### Phase 2: Test Results History Page
1. Create database method `get_all_test_runs()`
2. Create API endpoint `GET /api/test-runs`
3. Update API response to include test components instead of phase numbers
4. Create frontend page `/history.html`
5. Implement table with sorting/filtering
6. Add pagination
7. Create detail view/modal
8. Add export functionality

### Phase 3: Integration & Polish
1. Add navigation between pages
2. Link test results to history page
3. Add "Re-test" functionality from history
4. Remove all "phase" terminology from UI and API responses
5. Performance optimization
6. Error handling and edge cases
7. Documentation updates

---

## API Changes for Test Component Selection

### Request Format Change

**Old Format (Phase-based):**
```http
POST /api/streams/check
Content-Type: application/json

{
  "url": "https://example.com/stream.mp3",
  "phase": 4
}
```

**New Format (Component-based):**
```http
POST /api/streams/check
Content-Type: application/json

{
  "url": "https://example.com/stream.mp3",
  "tests": {
    "connectivity": true,
    "stream_info": true,
    "player_test": true,
    "audio_analysis": true,
    "ad_detection": true
  }
}
```

**Backend Mapping:**
- `connectivity: true` → Run Phase 1 (connectivity, SSL, headers)
- `stream_info: true` → Run Phase 1 (parameters, metadata, stream type)
- `player_test: true` → Run Phase 2
- `audio_analysis: true` → Run Phase 3
- `ad_detection: true` → Run Phase 4

**Validation:**
- At least one test component must be selected
- `connectivity` is required if any other test is selected (dependency)
- Invalid combinations rejected with clear error messages

### Response Format Change

**Remove:**
- `"phase": 4` field

**Add:**
- `"tests_completed": ["connectivity", "stream_info", "player_test", ...]` array
- `"tests_requested": ["connectivity", "stream_info", ...]` array (what user selected)

## Technical Requirements

### Frontend
- **No new dependencies** (use existing vanilla JS)
- **CSS Variables** for theme colors (easy dark/light toggle)
- **Responsive design** (mobile-first approach)
- **Accessibility** (WCAG 2.1 AA compliance)
- **Checkbox UI** with icons and tooltips

### Backend
- **Efficient database queries** (avoid N+1 queries)
- **Pagination** for large result sets
- **Error handling** for database failures
- **Input validation** for query parameters
- **Test component mapping** to internal phase logic
- **Backward compatibility** (accept both old `phase` and new `tests` format during transition)

### Database
- **Indexes** on frequently queried fields
- **Query optimization** for large datasets
- **Data retention** policy (optional: archive old results)
- **Migration**: Update existing records to include `tests_completed` field (optional)

---

## Success Criteria

### Dark Mode Redesign
- ✅ Professional, technical appearance
- ✅ Improved information density
- ✅ Better readability in dark theme
- ✅ All existing functionality preserved
- ✅ Responsive on all devices
- ✅ Checkbox-based test selection (no phase terminology)
- ✅ Clear, user-friendly test component labels

### Test Component Selection
- ✅ Checkbox UI replaces phase dropdown
- ✅ All test components clearly labeled
- ✅ Default to all tests selected
- ✅ Validation ensures at least one test selected
- ✅ API accepts component-based requests
- ✅ No "phase" terminology visible to users

### Test Results History
- ✅ Display all test results in table format
- ✅ Sortable and filterable columns
- ✅ Pagination for large datasets
- ✅ Fast load times (< 2 seconds for 100 results)
- ✅ Detail view shows complete test data
- ✅ Shows tests completed (not phase numbers)
- ✅ Export functionality works

---

## Future Enhancements (Out of Scope)

- **Charts/Graphs**: Visualize trends over time
- **Real-time Updates**: WebSocket for live test results
- **Advanced Filtering**: Complex query builder
- **Bulk Actions**: Select multiple tests for operations
- **Comparison View**: Side-by-side test comparison
- **Alerts/Notifications**: Notify on test failures
- **Dashboard Widgets**: Customizable dashboard layout
