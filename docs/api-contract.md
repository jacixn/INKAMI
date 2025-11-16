# API Contract (MVP)

## POST `/api/chapters`

| field | type | description |
| --- | --- | --- |
| files | multipart form-data | ZIP/PDF/image bundle of chapter pages |

**Response**
```json
{
  "chapter_id": "uuid",
  "job_id": "uuid"
}
```

## GET `/api/chapters/{chapter_id}`

Returns processing state and processed pages once ready.

```json
{
  "chapter_id": "uuid",
  "status": "processing | ready | failed",
  "progress": 42,
  "pages": [
    {
      "page_index": 0,
      "image_url": "https://cdn/page.png",
      "items": [
        {
          "bubble_id": "bubble_1",
          "bubble_box": [x1, y1, x2, y2],
          "panel_box": [x1, y1, x2, y2],
          "type": "dialogue",
          "speaker_id": "char_01",
          "speaker_name": "MC",
          "voice_id": "voice_friendly_f",
          "text": "Hello world",
          "audio_url": "https://cdn/audio.mp3",
          "word_times": [
            { "word": "Hello", "start": 0, "end": 0.42 }
          ]
        }
      ],
      "reading_order": ["bubble_1", "bubble_3"]
    }
  ]
}
```

## GET `/api/jobs/{job_id}`

Poll background job progress.

```json
{
  "job_id": "uuid",
  "status": "queued|processing|ready|failed",
  "progress": 65,
  "chapter_id": "uuid"
}
```

## PATCH `/api/bubbles/{speaker_id}`

Update speaker metadata + voice assignment.

```json
{
  "voice_id": "voice_brash_m",
  "display_name": "Rival"
}
```

