# Operasyon arayüzü

Kontrol odası ekranları:

- **Filo** (`/`): ilgi bekleyen panoların iş listesi ve sınıra kalan süre ekseni.
- **Pano detayı** (`/pano/:pano_id`): ön görünüş ikizi ve alarm için Neden / Ne yapmalı / Ne kadar acil.

Tasarım yönü "RAL 7035" (ISA-101 yüksek performanslı HMI, renk yalnızca anormal durumda). Gerekçesi `docs/16-ux-tasarim.md`'de yazılacak. Atılabilir denemeler `sketches/` altında; üretim paketine girmez.

| Komut | Ne yapar |
|---|---|
| `npm install` | Bağımlılıkları kurar |
| `npm run dev` | <http://localhost:5173>; API ve WebSocket'i `localhost:8000`'e yönlendirir (`GRIDUP_BACKEND` ile değişir) |
| `npm run dev:mock` | Backend olmadan örnek veriyle çalışır; üstte "Örnek veri" şeridi görünür |
| `npm test` | Birim testleri; alarm kodu sözlüğünün ve çizim noktalarının sözleşmelerle eşleştiğini de denetler |
| `npm run build` | Tip denetimi ve üretim paketi (`dist/`) |

Yığında: `docker compose -f deploy/compose.yaml up -d --build` → <http://localhost:3000>

## Kurallar

- API alan adları yalnızca `src/api/types.ts`'te tanımlanır (`contracts/openapi.yaml` karşılığı). Eksik alan `contracts/changes/` ile istenir.
- Eşik değerleri arayüze gömülmez (PLAN.md kural 10): nokta rengi API'nin `ConnPoint.state` alanından, eşik sayıları `reason.signals[].threshold`'dan gelir.
- Arayüz metni Türkçe; kod → metin sözlüğü `src/lib/labels.ts`.
- Yazı tipleri npm paketinden gelir, çalışma anında internet gerekmez.
