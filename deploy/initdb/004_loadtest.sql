-- Yuk testi olcumleri (TB3 Adim 4-5, Kisi B).
-- loadtest/fleet.py yazar (her calistirmada bu dosyayi idempotent olarak yeniden uygular: mevcut
-- veritabaninda initdb tekrar calismaz), Grafana "Olcek" panosu okur. Uretim verisi DEGILDIR.

CREATE TABLE IF NOT EXISTS loadtest_metrics (
    ts      TIMESTAMPTZ      NOT NULL,
    run_id  TEXT             NOT NULL,   -- or. 20260913T153000-1000p
    metric  TEXT             NOT NULL,   -- or. backend_cpu_pct, receive_p95_ms, publish_per_s
    value   DOUBLE PRECISION
);

SELECT create_hypertable('loadtest_metrics', 'ts',
                         chunk_time_interval => INTERVAL '7 days',
                         if_not_exists      => TRUE);

CREATE INDEX IF NOT EXISTS loadtest_metrics_run_idx ON loadtest_metrics (run_id, metric, ts DESC);
