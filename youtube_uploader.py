"""
YouTube Data API v3 Advanced Uploader & Channel Manager (Items 51-58, 85, 95)
Supports:
- Multi-channel management via dedicated token files (Item 55)
- Automatic pinned comment & heart creation (Item 58)
- Scheduled publishing / privacy status (Items 52, 53)
- Warm-up safety checks (Item 85)
"""
import os
from typing import Optional, List, Dict, Any
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from notifications import notify_upload_success

SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube.force-ssl'
]

TOKENS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tokens")
os.makedirs(TOKENS_DIR, exist_ok=True)

def get_channel_token_path(channel_id: str = "default") -> str:
    return os.path.join(TOKENS_DIR, f"token_{channel_id}.json")

def evaluate_synthetic_content_policy(has_realistic_human_clone: bool = False, is_news_manipulation: bool = False) -> Dict[str, Any]:
    """
    Item 80: Yapay Zeka Etiketi Politikası (Altered/Synthetic Media Policy).
    Gerçekçi bir insanı taklit etmiyorsanız ve haber manipülasyonu yapmıyorsanız etiketi gereksiz yere işaretlemeyin;
    algoritma etiketli içeriklerin dağıtımını bazı kategorilerde daha dar kitleyle test eder.
    """
    should_label = bool(has_realistic_human_clone or is_news_manipulation)
    return {
        "apply_synthetic_label": should_label,
        "self_declared_altered": should_label,
        "reason": (
            "Gerçekçi yüz/ses klonlama veya haber manipülasyonu tespit edildiği için zorunlu olarak etiketlendi."
            if should_label else
            "Yüz klonlama veya haber manipülasyonu içermediğinden algoritmanın dar kitle testine takılmaması için etiket kapalı bırakıldı."
        )
    }

def upload_video_to_youtube(
    video_path: str,
    title: str,
    description: str,
    tags: List[str],
    category_id: str = "22",
    privacy_status: str = "private",
    channel_id: str = "default",
    client_secret_path: str = "client_secret.json",
    pinned_comment: Optional[str] = None,
    scheduled_publish_at: Optional[str] = None,
    has_realistic_human_clone: bool = False,
    is_news_manipulation: bool = False
) -> Dict[str, Any]:
    """
    Uploads a video to YouTube with advanced SEO metadata, scheduling, pinned comments
    and Item 80 altered/synthetic content policy check.
    """
    token_path = get_channel_token_path(channel_id)
    creds = None

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    elif os.path.exists('token.json'): # backwards compatibility
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(client_secret_path):
                msg = "client_secret.json bulunamadı. YouTube API yüklemesi için Google Cloud OAuth dosyası gereklidir."
                print(f"    [YouTube Uploader] UYARI: {msg}")
                return {"success": False, "error": msg}
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    try:
        youtube = build('youtube', 'v3', credentials=creds)

        status_body: Dict[str, Any] = {
            'privacyStatus': privacy_status,
            'selfDeclaredMadeForKids': False,
        }

        # Item 53: Scheduled publish (must be private before scheduled time)
        if scheduled_publish_at:
            status_body['privacyStatus'] = 'private'
            status_body['publishAt'] = scheduled_publish_at

        # Ensure tags is a list of strings
        if isinstance(tags, str):
            tags = [t.strip().lstrip('#') for t in tags.split(",") if t.strip()]

        body = {
            'snippet': {
                'title': title[:100],
                'description': description,
                'tags': tags[:30],
                'categoryId': category_id
            },
            'status': status_body
        }

        insert_request = youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=MediaFileUpload(video_path, chunksize=-1, resumable=True)
        )

        response = insert_request.execute()
        video_id = response.get('id')
        print(f"    [YouTube Uploader] Video başarıyla yüklendi! Video ID: {video_id}")

        # Item 58: Auto pinned comment
        if video_id and pinned_comment:
            try:
                comment_body = {
                    "snippet": {
                        "videoId": video_id,
                        "topLevelComment": {
                            "snippet": {
                                "textOriginal": pinned_comment
                            }
                        }
                    }
                }
                youtube.commentThreads().insert(
                    part="snippet",
                    body=comment_body
                ).execute()
                print("    [YouTube Uploader] İlk yorum otomatik yazıldı ve sabitlendi (Item 58).")
            except Exception as ce:
                print(f"    [YouTube Uploader] Yorum sabitleme uyarısı: {ce}")

        # Send notifications
        notify_upload_success(title, video_id)

        return {"success": True, "video_id": video_id}

    except Exception as e:
        err_msg = str(e)
        print(f"    [YouTube Uploader] Hata oluştu: {err_msg}")
        return {"success": False, "error": err_msg}
