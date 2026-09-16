# Graph Report - griduphackathon  (2026-09-16)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 4023 nodes · 8367 edges · 186 communities (161 shown, 25 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 430 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c4993739`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- evaluate
- threshold_sweep.py
- test_profiles.py
- test_alarm_manager.py
- fleet.py
- PanelSimulator
- test_quality.py
- score
- views.py
- mock.ts
- test_notifier.py
- Ikiz3D.tsx
- EdgePipeline
- panosim.py
- ModbusTcpServer
- Alarm
- ScadaGateway
- iec104_server.py
- test_modbus_tcp.py
- test_scenarios.py
- test_threshold_sweep.py
- test_scada_encoder.py
- test_iec104_server.py
- create_app
- labels.ts
- gen_iec104_doc.py
- test_map_loader.py
- test_loadtest_physics.py
- test_risk.py
- package.json
- dispatcher.py
- test_api_alarms.py
- virtual_gsm_modem.py
- PanoDetay.tsx
- scenarios.py
- test_generator.py
- OlayAnalizi.tsx
- SmsModem
- test_api_insights.py
- test_digest.py
- test_prognostics.py
- MemoryStore
- worklist.ts
- seed_demo.py
- properties
- RiskEngine
- test_iec104_points.py
- test_grafana_dashboards.py
- properties
- CentralDetector
- Tvoc2Device
- alarm_service.py
- RegisterMap
- properties
- main.py
- _Connection
- test_api_panels.py
- properties
- properties
- KIndexEstimator
- run
- test_panosim_scenario.py
- encoder.py
- properties
- panoalgo/validate.py
- test_tvoc2_server.py
- encode
- AlarmKonsolu.tsx
- Mpr53csDevice
- test_central_detector.py
- WhatsAppClient
- test_panobeyni_sim.py
- Contracts
- test_scada_gateway.py
- ingest.py
- PgStore
- db.py
- MqttSubscriber
- rls.c
- AlarmManager
- test_seed_demo.py
- test_devices.py
- modbus_map.c
- backend/tests/helpers.py
- encode_submit
- x-topics
- mockSeries.ts
- IngestPipeline
- ExceptionCode
- risk
- gen_grafana_dashboards.py
- PointValue
- panoalgo/tests/conftest.py
- test_db_integration.py
- prognostics.py
- StreamHub
- pdu.py
- test_sms_modem.py
- Store
- Notifier
- properties
- 001_schema.sql
- compilerOptions
- test_detect.py
- dew_point
- make_rig
- properties
- properties
- time_to_limit
- DeviceReader
- test_alarm_store.py
- Client
- detect.py
- test_loadtest_storage.py
- .__init__
- Tvoc2Block
- LoopThread
- _ortak.sh
- MprBlock
- RateMeter
- panoalgo/tests/helpers.py
- test_gen_modbus_doc.py
- pano_dew_point
- RingBuffer
- test_gen_iec104_doc.py
- items
- pano_limits_evaluate
- in_alpha_band
- vectors.py
- _feed
- test_compression.py
- acked_codes
- mqtt-telemetry.schema.json
- scenario-labels.schema.json
- Api
- GatewayStations
- PromptCheckingPort
- t_conn
- main
- predictions_from_series
- test_k_index.py
- duman-testi.sh
- main
- format_pano_id
- alpha_lambda
- relative_accuracy
- gen_alarm_doc.py
- .add_listener
- expect
- thermal.c
- parse_units
- alarms
- .record_trip
- check_contracts.py
- l0_breach_at
- scenario_id
- .__init__
- UnknownTypeError
- generated_at
- pano_id
- pano_type
- seed
- t_start
- 004_loadtest.sql
- vite-env.d.ts
- .freeze_baseline
- test_docs_12_matches_what_the_generator_produces_now
- notify/__init__.py
- engine
- s0.sh
- s1.sh
- s2.sh
- s3.sh
- s4.sh
- s5.sh
- s6.sh
- s7.sh
- s8.sh
- 006_demo_seed.sql
- uret-stl.sh
- test_winter_night_can_drive_the_dew_point_margin_into_condensation
- test_the_sensor_fault_scenario_produces_prognoses_without_any_breach
- panoalgo

## God Nodes (most connected - your core abstractions)
1. `MemoryStore` - 63 edges
2. `PanelSimulator` - 60 edges
3. `Alarm` - 59 edges
4. `Contracts` - 56 edges
5. `IngestPipeline` - 46 edges
6. `observe()` - 46 edges
7. `evaluate()` - 45 edges
8. `utc()` - 45 edges
9. `AlarmService` - 43 edges
10. `cond()` - 43 edges

## Surprising Connections (you probably didn't know these)
- `Tvoc2Block` --uses--> `Tvoc2Device`  [INFERRED]
  sim/tvoc2_sim.py → libs/panoalgo/panoalgo/devices.py
- `MprBlock` --uses--> `Mpr53csDevice`  [INFERRED]
  sim/mpr53cs_sim.py → libs/panoalgo/panoalgo/devices.py
- `build_payload()` --uses--> `EdgePipeline`  [INFERRED]
  sim/panobeyni_sim.py → libs/panoalgo/panoalgo/edge.py
- `main()` --uses--> `EdgePipeline`  [INFERRED]
  sim/panobeyni_sim.py → libs/panoalgo/panoalgo/edge.py
- `_run_stream()` --uses--> `EdgePipeline`  [INFERRED]
  sim/panosim.py → libs/panoalgo/panoalgo/edge.py

## Import Cycles
- 3-file cycle: `backend/app/alarm_service.py -> backend/app/notify/dispatcher.py -> backend/app/notify/templates.py -> backend/app/alarm_service.py`
- 4-file cycle: `backend/app/alarm_service.py -> backend/app/db.py -> backend/app/notify/dispatcher.py -> backend/app/notify/templates.py -> backend/app/alarm_service.py`

## Communities (186 total, 25 thin omitted)

### Community 0 - "evaluate"
Cohesion: 0.05
Nodes (74): Repo icindeki contracts/ dizini — dosya sistemi sorgusu bir kez yapilir.…, default_contracts_dir(), _electrical(), _environment(), evaluate(), load_contract(), _partial_discharge(), _phase_difference() (+66 more)

### Community 1 - "threshold_sweep.py"
Cohesion: 0.05
Nodes (60): ArgumentParser, calc(), fixture, F-05 — scripts/tazminat_maruziyeti.py: parametre yoksa "veri yok", parametre…, Dokumana elle yazilan adet ve fiyatlar betigin turettikleriyle ayni kalmali., test_docs_10_bom_farki_tablosu_koddaki_sayilarla_ayni(), test_odenen_arayuz_fiyati_bom_csv_satirindan_gelir(), _amount() (+52 more)

### Community 2 - "test_profiles.py"
Cohesion: 0.05
Nodes (61): Kenar tespit boru hatti (TA2 Adim 6, Kisi A): ham fizik yuku -> zengin…, Fizik tabanli sentetik telemetri ureteci (TA1 Adim 5, Kisi A). Neden ureteci:…, ar1_phi(), Ar1Noise, hour_of_week(), load_profile(), datetime, ProfileKind (+53 more)

### Community 3 - "test_alarm_manager.py"
Cohesion: 0.08
Nodes (65): at(), cond(), hyst(), manager(), observe(), datetime, fixture, parametrize (+57 more)

### Community 4 - "fleet.py"
Cohesion: 0.06
Nodes (49): alarm_latencies(), build_factory(), cleanup(), clock_offset_s(), Config, _get_json(), main(), parse_docker_stats() (+41 more)

### Community 5 - "PanelSimulator"
Cohesion: 0.05
Nodes (26): PanelSimulator, PointSpec, Bir olcum noktasinin degismez fiziksel kimligi., Tek bir panonun kenar telemetrisini uretir. Ayni `seed` ayni diziyi verir:…, Son adimda bu noktadan gecen akim (A)., Yuku sabitler: profil, mevsim ve gurultu devre disi kalir. Isil modelin kararli…, Bir noktanin isil direnc indeksini K0'in katina cikarir (gevsek baglanti).…, Yuku olcekler (asiri yuk senaryosu). K'ye DOKUNMAZ — ariza degil. (+18 more)

### Community 6 - "test_quality.py"
Cohesion: 0.07
Nodes (56): _by_point(), check(), codes_from_bits(), default_contracts_dir(), _elapsed_minutes(), load_contract(), point_quality(), Path (+48 more)

### Community 7 - "score"
Cohesion: 0.06
Nodes (55): default_contracts_dir(), _discriminator_holds(), load_contract(), Any, NamedTuple, Path, L3 hipotez fuzyonu (TA2 Adim 6, Kisi A): alarm kodlari -> baskin hipotez +…, Sozlesmedeki `discriminator` kosulunu uygular. Su an yalnizca HYP-OVERLOAD'da… (+47 more)

### Community 8 - "views.py"
Cohesion: 0.08
Nodes (47): _aware(), bucket_starts(), event_blackbox(), fill(), fleet_kpi(), nearest_rank(), panel_series(), parse_step() (+39 more)

### Community 9 - "mock.ts"
Cohesion: 0.07
Nodes (47): api, httpApi, usingMocks, ADVICE, alarm(), allAlarms(), basePoints(), BLACKBOX_PANEL_TAGS (+39 more)

### Community 10 - "test_notifier.py"
Cohesion: 0.07
Nodes (44): NotifyConfig, _numbers(), calls(), gateway(), manager(), fixture, parametrize, Request (+36 more)

### Community 11 - "Ikiz3D.tsx"
Cohesion: 0.09
Nodes (39): ConnPoint, Tvoc, ALL_POINTS, buildScene(), paintNode(), DETECTOR_X, HistorySample, HOME_OFFSET (+31 more)

### Community 12 - "EdgePipeline"
Cohesion: 0.09
Nodes (35): lambda_for_period(), Unutma faktorunu farkli bir ornekleme periyoduna tasir (ayni ZAMAN hafizasi). T…, EdgePipeline, expected(), _forget_estimates(), datetime, Yuku YERINDE zenginlestirir ve ayni sozlugu doner., Ornekleme periyodunu ardisik zaman damgalarindan cikarir. (+27 more)

### Community 13 - "panosim.py"
Cohesion: 0.08
Nodes (37): Pano ici anomali tespiti ve fizik tabanli sentetik veri uretimi (Kisi A)., build_payload(), main(), parse_args(), FrameType, Namespace, Pano Beyni tasima kabugu (TA3 Adim 6, Kisi A): Modbus master -> kenar -> MQTT.…, Olculen buyuklukleri isil modelle birlestirip sema-gecerli telemetri uretir.… (+29 more)

### Community 14 - "ModbusTcpServer"
Cohesion: 0.06
Nodes (19): Iec104Server, StreamReader, StreamWriter, client_allowed(), _close(), DeviceModel, ModbusTcpServer, normalize_peer() (+11 more)

### Community 15 - "Alarm"
Cohesion: 0.09
Nodes (19): Alarm, Depodan yuklenen acik alarmlari geri koyar (yeniden baslatma). Depodaki…, AlarmService, _digest_summary(), datetime, Acik alarmlari ve panolarin son gorulme zamanini depodan bir kez yukler…, Ingest dinleyicisi: yazilan her partiden sonra (yazici thread'inde) cagrilir., Alarm zamanlayicisi: bekleyen yazimlar, raf suresi, haberlesme denetimi. (+11 more)

### Community 16 - "ScadaGateway"
Cohesion: 0.09
Nodes (24): PanelImage, _Panel, Any, CommandSink, datetime, SCADA ag gecidi (TB3 Adim 2, Kisi B): Modbus birimi -> pano, register…, /health icin ozet: eslenen birim, bellekte izlenen pano, yazma durumu, kilitli…, Kilit altinda: panonun kaydi; sabit eslemede eslenmemis pano izlenmez. Yeni… (+16 more)

### Community 17 - "iec104_server.py"
Cohesion: 0.09
Nodes (40): decode_apdu(), encode_asdu(), encode_i(), encode_s(), encode_u(), float_element(), IFrame, parse_cp56time2a() (+32 more)

### Community 18 - "test_modbus_tcp.py"
Cohesion: 0.11
Nodes (34): client(), device(), frame(), is_closed(), loop(), MemoryDevice, fixture, parametrize (+26 more)

### Community 19 - "test_scenarios.py"
Cohesion: 0.07
Nodes (41): build(), Senaryoyu kosturur; (DataFrame, etiket sozlugu) doner. Etiket sozlugu…, _contract_points(), _lead_time_h(), fixture, parametrize, Etiketli senaryo ureteci testleri — PLAN.md TA2 Adim 7. Beklenen degerlerin…, l0_breach_at = 70 K'nin asildigi an; sabit esik ancak BURADA uyarir. (+33 more)

### Community 20 - "test_threshold_sweep.py"
Cohesion: 0.06
Nodes (37): condense(), healthy(), _pair(), fixture, Ciy noktasi esik taramasi (F-06) — scripts/threshold_sweep.py. Beklenen…, Yeniden kosturma contracts/ dizininin GECICI kopyasini yazar, aslini degil., docs/12 §3: S0'da 71,4 yanlis alarm/100 pano/gun, tamami ALM-DEW-*., Taramanin ana bulgusu: esigi kismak olay sayisini AZALTMIYOR, artiriyor. (+29 more)

### Community 21 - "test_scada_encoder.py"
Cohesion: 0.12
Nodes (41): EventLog, Ag gecidinin gordugu son alarm acilislari (event blogu)., alarm(), coils(), encoder(), fixture, parametrize, TB3 Adim 2 — pano son durumu + alarm yoneticisi -> Pano Beyni register… (+33 more)

### Community 22 - "test_iec104_server.py"
Cohesion: 0.11
Nodes (41): cp56time2a(), decode_asdu(), CP56Time2a, UTC (yaz saati biti 0): ms (2) | dakika | saat | gun + haftanin…, Timing, utc(), Sayilar ve etiketler oncelik tablosundan gelir; P2 (anlik yol) ve pencere disi…, test_digest_counts_only_the_p3_and_sys_alarms_of_the_window(), test_decode_general_interrogation_command() (+33 more)

### Community 23 - "create_app"
Cohesion: 0.11
Nodes (33): _csv(), Settings, _configure_logging(), create_app(), Uygulama kayitlari (gridup.*) konteyner loguna duser; uvicorn kendi…, Clock, datetime, Uygulama bozuksa test sonsuza dek beklemesin diye zaman asimli WebSocket… (+25 more)

### Community 24 - "labels.ts"
Cohesion: 0.08
Nodes (35): AlarmSignal, NotifyChannel, PointState, AlarmNedeni(), Props, SignalRow(), formatter(), formatters (+27 more)

### Community 25 - "gen_iec104_doc.py"
Cohesion: 0.12
Nodes (38): Register/coil adi -> merkezdeki kaynagi (docs/03 ureteci icin)., source_docs(), _cell(), _default(), emitted_types(), field_widths(), _fits(), interop_application() (+30 more)

### Community 26 - "test_map_loader.py"
Cohesion: 0.11
Nodes (32): _check_overlaps(), Coil, load_map(), MapError, _parse_block(), _parse_coils(), parse_map(), Any (+24 more)

### Community 27 - "test_loadtest_physics.py"
Cohesion: 0.06
Nodes (31): fleet(), fixture, parametrize, TB3 Adim 4 — loadtest/fleet.py yuk aracinin saf parcalari (canli olcum…, 100 B/satir, mesaj basina 86 satir, 10 s periyot: 100 pano -> 100 x 8640 x 86 x…, Yuk testindeki alarm gercek zinciri calistirmali: kenar kodu + esigi asan K/K0…, test_alarm_payload_is_explained_as_k_alarm_by_the_risk_engine(), test_parse_docker_stats() (+23 more)

### Community 28 - "test_risk.py"
Cohesion: 0.09
Nodes (38): by_key(), hypothesis(), parametrize, TB2 Adim 4 — risk motoru: telemetri ornegi -> aciklanabilir alarm kosullari…, Esik degerleri alarm-codes.yaml ile elle eslestirildi (70/105/1.6/1.0/45 ...)., ALM-PD-TREND iki hipotezin kaniti: kenarin baskin modu hangisiyse onun onerisi., Fuzyon yalnizca ESLESEN kaniti dondurur; eksik kanit burada hipotez tanimindan…, Ornegi uretimdeki gibi ingest ayristiricisindan gecirir (sema + ts denetimi… (+30 more)

### Community 29 - "package.json"
Cohesion: 0.05
Nodes (37): dependencies, @fontsource/barlow, @fontsource/barlow-semi-condensed, react, react-dom, react-router-dom, three, devDependencies (+29 more)

### Community 30 - "dispatcher.py"
Cohesion: 0.12
Nodes (31): Digest, Gunde bir kez gonderilen ozetin icerigi; metne cevirmek bildirim katmaninin…, _Job, Bildirim ag gecidi (TB2 Adim 5-7, Kisi B): alarm degisikligi -> kanal isleri ->…, Gunluk ozet: alarm servisi gunde bir kez cagirir, saha ekibine tek parca SMS…, gsm7_septets(), Metin GSM-7'ye sigmiyorsa None., digest_sms() (+23 more)

### Community 31 - "test_api_alarms.py"
Cohesion: 0.13
Nodes (36): app(), by_code(), client(), clock(), hypothesis_advice(), list_alarms(), make_app(), fixture (+28 more)

### Community 32 - "virtual_gsm_modem.py"
Cohesion: 0.08
Nodes (18): mask_number(), Kisisel veri azaltma (KVKK): kayit ve denetim izinde telefon numarasi acik…, +905550000001' -> '+90******0001'. Kisa veya alfanumerik gonderici oldugu gibi…, _control(), _error(), FileLog, main(), ModemServer (+10 more)

### Community 33 - "PanoDetay.tsx"
Cohesion: 0.08
Nodes (29): request(), ApiError, errorText(), buildPath(), ChartSeries, CizgiGrafik(), fmtDay, fmtTime (+21 more)

### Community 34 - "scenarios.py"
Cohesion: 0.08
Nodes (35): parse_detector(), X2:4" -> ("X2", 4). None girdi None doner; gecersiz ad ValueError. Ad bicimi…, Ark korumasi dedektor sagligi: False = pano sessizce korumasiz. `detector`…, _default_fixture_dir(), _in_comms_gap(), _inject(), iter_samples(), _labels() (+27 more)

### Community 35 - "test_generator.py"
Cohesion: 0.09
Nodes (35): make(), datetime, Sentetik veri ureteci testleri — PLAN.md TA1 Adim 6. Beklenen degerlerin…, Sema deseni ^[A-Z]{3}-[0-9]{5}$ — hata yayin aninda degil, kurulumda cikmali., Sabit akimda dT -> K*I^2 (rapor 15.1 kararli durum)., Bir tau sonunda adim yanitinin ~%63'u tamamlanmis olmali (1 - 1/e)., Rapor 15.2: tau = 10-30 dk., Rapor 15.2: olcum gurultusu sigma ~ 0,2 degC. Gurultusuz seri juriye sahte bir… (+27 more)

### Community 36 - "OlayAnalizi.tsx"
Cohesion: 0.12
Nodes (26): App(), FleetKpis(), NAV, StatusStrip(), ChartMarker, ago(), panoTypeText(), useNow() (+18 more)

### Community 37 - "SmsModem"
Cohesion: 0.11
Nodes (16): ModemError, RuntimeError, Tamponlanan ve `timeout_s` icinde gelen SMS'leri teslim eder., Son sonuc koduna (OK / hata) kadar bilgi satirlari; yanki ve istem ayiklanir., Bir sonraki anlamli satir. Gelen SMS (+CMT basligi + PDU satiri) burada…, Komut beklenmezken (poll, calma suresi) gelenleri okur; gelen SMS'ler…, Tampondan tamamlanmis bir satir; '> ' istemi satir sonu beklemeden tek basina…, `quiet_s` boyunca yeni bayt gelmeyene kadar okur ve atar. (+8 more)

### Community 38 - "test_api_insights.py"
Cohesion: 0.10
Nodes (28): get_series(), incident(), iso(), datetime, fixture, parametrize, Analiz uclari (TB3, C'nin TC3 ekranlari bekliyor): /panels/{id}/series,…, from 10:00:40 -> ilk kova 10:00:00'dan baslar; 10:00:30 ornegi o kovadadir ama… (+20 more)

### Community 39 - "test_digest.py"
Cohesion: 0.08
Nodes (21): DigestSink, fixture, time, TB2 Adim 7 — P3 gunluk ozeti ve SYS toplu ozeti (app.alarm_service ->…, Uctan uca: alarm zamanlayicisinin tick'i -> ozet -> sanal GSM modem, tek parca…, Isaret alarms tablosundadir: yeni alarm servisi bellekteki gunu bilmese de…, Ozet saati yapilandirilabilir: 21:30'a ayarli servis 21:29'da hic kimseye…, DIGEST_AT="" -> ozet kapali; alarm servisi Settings olmadan kuruldugu icin… (+13 more)

### Community 40 - "test_prognostics.py"
Cohesion: 0.09
Nodes (32): convergence(), prognostic_horizon(), Tahminin bir daha konidan cikmadigi ilk anin t_EOL'e uzakligi (saat). Tanim…, (yakinsama uzakligi saat, pencere icindeki kesri) — Saxena ve ark. 2010. x_c =…, _perfect(), Prognoz geri testi olcutleri (F-04) — panoalgo/prognostics.py. Beklenen…, None ile 0 ayri seydir: 0 'tam ihlal aninda tuttu' demektir., n = 1 durustluk kaydi: geri testi yapilabilen TEK yorunge var. (+24 more)

### Community 41 - "MemoryStore"
Cohesion: 0.11
Nodes (12): RuntimeError, Gecici depolama hatasi (baglanti yok, zaman asimi). Tekrar denenebilir; API 503…, StoreError, Request, _store_unavailable(), MemoryStore, datetime, `app.db.Store` sozlesmesinin bellek ici test cifti. Uretimde PgStore… (+4 more)

### Community 42 - "worklist.ts"
Cohesion: 0.12
Nodes (26): Alarm, PanelDetail, PAD, Props, RiskMatrisi(), X_TICKS_H, xTickLabel(), Pin() (+18 more)

### Community 43 - "seed_demo.py"
Cohesion: 0.11
Nodes (32): already_seeded(), apply_migrations(), DemoPanel, _digest_changes(), _digest_sample(), generate(), main(), _plan() (+24 more)

### Community 44 - "properties"
Cohesion: 0.07
Nodes (32): maximum, minimum, type, additionalProperties, description, properties, required, type (+24 more)

### Community 45 - "RiskEngine"
Cohesion: 0.17
Nodes (16): Condition, Bir ornekte dogru olan alarm kosulu; `reason`/`advice`/`ttl_h` alarm olustugu…, _exceeds(), _neutral_harmonics(), _nodes(), _present(), Any, Risk motoru (TB2 Adim 4, Kisi B): telemetri ornegi -> aciklanabilir alarm… (+8 more)

### Community 46 - "test_iec104_points.py"
Cohesion: 0.11
Nodes (20): PanelEncoder, Register'in "yok" ham degeri (kaynagi bos oldugunda yazilan); bayraklarin "yok"…, MeasuredPoint, PointCatalog, Pano Beyni haritasi -> IEC 60870-5-104 bilgi nesneleri (TB3 Adim 8, Could, Kisi…, SinglePoint, by_ioa(), catalog() (+12 more)

### Community 47 - "test_grafana_dashboards.py"
Cohesion: 0.12
Nodes (28): eemua_rows(), expand_macros(), gen(), _panel_sql(), panels_of(), datetime, fixture, integration (+20 more)

### Community 48 - "properties"
Cohesion: 0.06
Nodes (31): description, type, description, type, description, type, description, type (+23 more)

### Community 49 - "CentralDetector"
Cohesion: 0.10
Nodes (27): CentralDetector, _is_central(), Any, Path, Merkez dedektor adaptoru (TA2, Kisi A): panoalgo -> backend kancasi.…, backend/app/risk.py CentralDetector Protocol'unun panoalgo uygulamasi., Yukun O AN ihlal ettigi sozlesme alarm kodlari., _point() (+19 more)

### Community 50 - "Tvoc2Device"
Cohesion: 0.06
Nodes (24): PDU 1000'e 1 yazilinca aktif trip temizlenir; LOG SILINMEZ, 149 azalmaz. Gercek…, Sensor arizasi: 222/223 ANCAK aktif hata varken anlamlidir (kilavuz 4.4.2)., Yazma DENEMESINI kaydeder. Cihaz kabul etse de bizim ag gecidimiz engeller; bu…, ABB TVOC-2 Arc Guard — salt okunur izleme arayuzu. HABERLESME KAPALI DAVRANISI:…, Tvoc2Device, Kilavuz 4.4.2: bu registerlar AKTIF HATA bilgisini tasir; hata yoksa 0x0000. '1…, Her trip blogu 6 okunabilir register + 1 BOSLUK (stride 7)., PDU 1000 aktif tripi temizler; log silinmez, 149 azalmaz. (Bizim ag gecidimiz… (+16 more)

### Community 51 - "alarm_service.py"
Cohesion: 0.11
Nodes (27): AlarmNotFound, AlarmNotSuppressible, AlarmStateConflict, RuntimeError, ISA-18.2 alarm yoneticisi (TB2, Kisi B). Saf durum makinesi: veritabani, ag ve…, Acik alarmlar arasinda bu kimlik yok (hic olmamis veya temizlenmis)., Istenen gecis alarmin su anki durumunda yapilamaz (or. iki kez onay)., Bastirilamaz oncelik (P1) rafa alinamaz. (+19 more)

### Community 52 - "RegisterMap"
Cohesion: 0.12
Nodes (23): Block, Blogun ilk bos adresi (dahil degil)., Araligin tamamini iceren blok; iki bloga veya bosluga tasan aralikta None., RegisterMap, _cell(), csv_bytes(), line_budget(), main() (+15 more)

### Community 53 - "properties"
Cohesion: 0.07
Nodes (30): description, type, description, minimum, type, additionalProperties, properties, required (+22 more)

### Community 54 - "main.py"
Cohesion: 0.10
Nodes (19): PeriodicWorker, Belirli aralikla bir islevi arka plan thread'inde calistirir; hata dongusu…, HTTP ve WebSocket uclari — sozlesme: contracts/openapi.yaml., Grid Up merkez uygulamasi (Kisi B)., lifespan(), _edge_command_sink(), _panel_update_publisher(), CommandSink (+11 more)

### Community 55 - "_Connection"
Cohesion: 0.17
Nodes (11): Asdu, group_objects(), Ayni tipteki ardisik degerleri ASDU basina en cok `limit` nesnelik gruplara…, _addressed(), _changed(), _Connection, ProtocolError, Exception (+3 more)

### Community 56 - "test_api_panels.py"
Cohesion: 0.10
Nodes (16): client(), gdz_payload(), ids(), ingest(), datetime, fixture, parametrize, TB1 — Panel API v1: contracts/openapi.yaml'a birebir uyum + turetilen alanlarin… (+8 more)

### Community 57 - "properties"
Cohesion: 0.07
Nodes (28): description, type, description, type, properties, description, description, type (+20 more)

### Community 58 - "properties"
Cohesion: 0.07
Nodes (28): additionalProperties, description, required, type, description, type, description, pattern (+20 more)

### Community 59 - "KIndexEstimator"
Cohesion: 0.09
Nodes (16): KIndexEstimator, KState, NamedTuple, Tek bir olcum noktasi icin K ve tau kestirimcisi. Kullanim: her ornekte…, Fiziksel araliga kirpilmis a kestirimi., Anlik K kestirimi. Negatif kestirim fiziksel degildir, sifira kirpilir., Anlik tau kestirimi (s); fiziksel araligin disina cikmaz., Dondurulmus taban; freeze_baseline() cagrilmadiysa None. (+8 more)

### Community 60 - "run"
Cohesion: 0.07
Nodes (28): Saglikli pano hicbir noktada 70 K artisi gecmemeli; gecerse S0 etiketi yalan…, Saglikli pano UYARI esigini (50 K) de gecmemeli, yalnizca alarm esigini degil.…, Rapor 15.2: 'Nem sicaklikla ters iliskili gunluk dongu'., Sartname 2.2.8.5: altta hava girisi, ustte cikis — cikis daha sicak olmali., Marj = YUZEY - ciy noktasi. Yuzey pano ici havadan sicak olamayacagi icin marj,…, Rapor 15.2: faz dengesizligi %2-15, yavas degisen., S0 normal senaryosunda asiri yuk YOK; ALM-I-OVER tetiklenmemeli., Konut panosunda aksam piki gece cukurundan belirgin yuksek olmali. (+20 more)

### Community 61 - "test_panosim_scenario.py"
Cohesion: 0.09
Nodes (25): published_payloads(), parametrize, panosim senaryo kipi (Kisi A, K1 + K3). Olculen iddialar: 1. `--scenario` demo…, --point senaryonun varsayilan noktasini gercekten degistirir., --detector X2:4 -> PDU 222'de 4. dedektorun biti 0 (kalanlar 1)., K3: `ts` artik duvar saatinin ONUNE GECMEZ; arayuzun `to = new Date()`…, --sim-clock eski davranisi geri verir (uzun vadeli veri uretimi icin)., Iki pano ayni saniyede yayinlayabilir; biri digerini ileri itmemeli. (+17 more)

### Community 62 - "encoder.py"
Cohesion: 0.15
Nodes (23): AlarmKey, _Facts, _firmware_code(), _get(), _item(), get(), _missing(), PanelSnapshot (+15 more)

### Community 63 - "properties"
Cohesion: 0.07
Nodes (27): type, description, type, properties, door_open, dt_air_k, rh_low_pct, rh_up_pct (+19 more)

### Community 64 - "panoalgo/validate.py"
Cohesion: 0.12
Nodes (23): _default_fixtures_dir(), _false_alarms(), load_layers(), main(), _prognosis_section(), Path, Dogrulama ve olcum (T4.1/T4.2, Kisi A): senaryo + etiket -> sayilar. PLAN.md…, Tek bir senaryoyu olcer. (+15 more)

### Community 65 - "test_tvoc2_server.py"
Cohesion: 0.12
Nodes (25): Popen, free_port(), sim/ testleri icin ortak yardimcilar (Kisi A)., Isletim sisteminden bos bir port ister ve hemen birakir., Alt surecin panoalgo'yu ve sozlesmeleri bulabilmesi icin ortam., sim/<script> dosyasini GERCEK CLI'siyla alt surec olarak baslatir., Port dinlemeye baslayana kadar bekler; acilmazsa testi dusurur., Ham Modbus TCP FC03 istegi gonderir; cevabi doner, cevap yoksa None. pymodbus… (+17 more)

### Community 66 - "encode"
Cohesion: 0.12
Nodes (21): encode(), pipeline(), fixture, TB1 — MQTT ingestion: dogrulama, uzun formata duzlestirme, karantina, toplu…, Veri hatasi tekrar denemekle gecmez; tek bozuk mesaj tum partiyi (tum filoyu)…, PostgreSQL text/JSONB NUL kabul etmez: ham yuk bile karantinaya yazilamazdi., store(), test_accepted_sample_carries_payload_and_receive_time() (+13 more)

### Community 67 - "AlarmKonsolu.tsx"
Cohesion: 0.10
Nodes (22): Seed, AlarmState, Prio, GLYPH, PrioMark(), Props, PRIO_NAME, prioRank() (+14 more)

### Community 68 - "Mpr53csDevice"
Cohesion: 0.10
Nodes (17): Mpr53csDevice, ENTES MPR-53CS sebeke analizoru — okunan degerler sozlesme olcegiyle. CT/VT…, I_primer = ham * 0.001 * CT => ham = I_primer / (0.001 * CT). Dogrulama (rapor…, PDU adresi -> 16-bit register degeri (32-bit olcumler iki register)., Rapor 15.1: 2309 A, CT 500 -> ham 4618., ham 5000 -> 5.000 A sekonder -> x500 = 2500 A primer (AT nominali)., Juri 0x8001'i okuyunca 500 gormeli., contracts/modbus-map.yaml word_order: high_first. (+9 more)

### Community 69 - "test_central_detector.py"
Cohesion: 0.10
Nodes (22): _central_detector(), panoalgo merkez dedektorunu yukler (TB2 Adim 4); yoksa GURULTULU sekilde gecer.…, CentralDetector, Protocol, Merkezde calisan tespit (or. panoalgo.quality.check + limits.evaluate)., fixture, TB2 Adim 4 — merkez dedektorun gercekten BAGLI oldugu (Kisi B, K5). Kanca 13…, ALM-COMMS-LOST ve ALM-DQ-* merkezin kendi mekanizmalarindir; dedektor onlari… (+14 more)

### Community 70 - "WhatsAppClient"
Cohesion: 0.13
Nodes (17): _error_detail(), Response, RuntimeError, WhatsApp Cloud API gondericisi (TB2 Adim 6, Kisi B) — IKINCIL kanal. On-…, Mesaj kimligini (wamid) dondurur; basarisizlikta WhatsAppError., WhatsAppClient, WhatsAppError, parametrize (+9 more)

### Community 71 - "test_panobeyni_sim.py"
Cohesion: 0.15
Nodes (24): _target(), cihazlar(), published(), fixture, Pano Beyni tasima kabugu (Kisi A, Y2): Modbus master -> kenar -> MQTT. TA3 Adim…, Elektriksel alanlar UYDURULMAZ: MQTT'ye giden deger Modbus'tan okunandir., --trip-after ile uretilen GERCEK trip, MQTT yukunde ALM-ARC-TRIP'e donusur. Bu…, --sensor-error: TVOC-2 hata biti -> prot_health_ok=False -> ALM-PROT-HEALTH. (+16 more)

### Community 72 - "Contracts"
Cohesion: 0.11
Nodes (18): _digest_prios(), time, Ozete girecek oncelikler sozlesmeden okunur: daily_digest: true (P3), sms:…, _command_topic(), Contracts, digest_at_from_env(), _ingest_topics(), parse_digest_at() (+10 more)

### Community 73 - "test_scada_gateway.py"
Cohesion: 0.13
Nodes (18): parse_modbus_password(), MODBUS_WRITE_PASSWORD: bos -> None (salt okunur); aksi halde 1-65535 (0,…, TB3 Adim 2 — SCADA ag gecidi (app.scada.gateway): birim -> pano, register…, Backend yeniden basladiginda panonun son durumu ve acik alarmlari, yeni…, registers(), test_ack_single_alarm_by_bit(), test_alarm_bits_and_summary_coils_after_ingest(), test_event_block_counts_alarm_openings() (+10 more)

### Community 74 - "ingest.py"
Cohesion: 0.13
Nodes (18): gridup/pano/{pano_id}/tel' -> MQTT abonelik filtresi 'gridup/pano/+/tel'., topic_filter(), _as_number(), _contains_nul(), flatten(), _NonFiniteNumber, Any, datetime (+10 more)

### Community 75 - "PgStore"
Cohesion: 0.15
Nodes (8): PgStore, datetime, timedelta, PostgreSQL/TimescaleDB deposu (psycopg 3 baglanti havuzu). Baglanti/zaman asimi…, [start, end) araligindaki TEMIZ (q = 0) olcumlerin `step` kovasi ortalamasi.…, Panonun alarm denetim izi, `at` [start, end] araliginda, zaman sirasiyla…, JournalEntry, alarm_journal satiri + ait oldugu alarmin kimligi (kara kutu zaman cizelgesi).

### Community 76 - "db.py"
Cohesion: 0.14
Nodes (19): _alarm_params(), Depolama katmani (Kisi B). `Store` sozlesmesini hem uretimdeki PgStore hem de…, EventRecord, Ic veri tipleri: ingest ciktilari ve depodan okunan pano kayitlari., events tablosu: olayi acan ilk alarm (kara kutu bu andan geriye bakar)., Delivery, notifications tablosu satiri: alici maskelidir., db() (+11 more)

### Community 77 - "MqttSubscriber"
Cohesion: 0.12
Nodes (14): MqttSubscriber, Broker'a baglanir, sozlesmedeki telemetri topic'lerine abone olur, mesajlari…, FakePahoClient, TB1 — MQTT abonesi: topic'ler sozlesmeden gelir, mesajlar boru hattina aynen…, paho.mqtt.client.Client'in MqttSubscriber'in kullandigi yuzeyi (ag yok)., Merkez -> kenar komutu (SCADA bakim modu / test alarmi): x-topics cmd sablonu…, Kopukken kuyruga alinmaz: gec teslim edilen eski komut sahada surpriz yaratir,…, _subscriber() (+6 more)

### Community 78 - "rls.c"
Cohesion: 0.24
Nodes (20): pano_real_t, clamp_a(), has_excitation(), pano_rls_excited(), pano_rls_freeze_baseline(), pano_rls_init(), pano_rls_k(), pano_rls_k_ratio() (+12 more)

### Community 79 - "AlarmManager"
Cohesion: 0.18
Nodes (10): AlarmManager, Change, _Event, Any, datetime, Panonun `ts` anindaki TUM dogru kosullari; listede olmayan kod o an yok sayilir., Merkezde uretilen kosul (or. haberlesme kopuklugu) `ts` aninda dogru.…, Basarili teslimde kanal alarmin `notified` listesine bir kez eklenir… (+2 more)

### Community 80 - "test_seed_demo.py"
Cohesion: 0.13
Nodes (20): dry_summary(), fixture, integration, skipif, F-01 — scripts/seed_demo.py: altin demo veritabani TEKRAR URETILEBILIR olmali.…, Gelecege tarihli satir canli veriyi backfill kuraline takar (app/db.py…, Tekrar uretilebilirlik: yazma yolu da (COPY + upsert + alarm yoneticisi)…, Sabit bir pencere sonu: iki kosunun ozeti ancak ayni pencerede birebir ayni… (+12 more)

### Community 81 - "test_devices.py"
Cohesion: 0.14
Nodes (18): date, days_since_epoch(), decode_hhmm(), encode_hhmm(), Cihaz register modelleri (TA3 Adim 1-2, Kisi A): TVOC-2 ve MPR-53CS. Iki gercek…, Tek register okur. None = ILLEGAL DATA ADDRESS (tanimsiz adres)., TVOC-2 tarih kodlamasi: 1970-01-01'den beri gun sayisi. Kilavuz ornegi: 0x42B6…, Saat kodlamasi: MSB saat, LSB dakika — IKILIK, BCD DEGIL. Kilavuz ornegi:… (+10 more)

### Community 82 - "modbus_map.c"
Cohesion: 0.19
Nodes (20): pano_gateway_t, pano_real_t, fully_inside_command(), is_read(), is_register_write(), pano_gateway_init(), pano_gateway_offer_password(), pano_k_ratio_register() (+12 more)

### Community 83 - "backend/tests/helpers.py"
Cohesion: 0.13
Nodes (17): load_contracts(), Path, publish(), api_contract(), contracts(), modem_log(), modem_server(), fixture (+9 more)

### Community 84 - "encode_submit"
Cohesion: 0.17
Nodes (19): decode_deliver(), decode_submit(), encode_submit(), _strip_smsc(), GSM modem SMS surucusu (TB2 Adim 5, Kisi B) — URETIM surucusudur. AT komutlari…, parametrize, TB2 Adim 5 — SMS PDU kodlayici (3GPP TS 23.040 / 23.038): app.notify.pdu.…, Elle kodlandi: OA 0B D0 'GRIDUP' (6 septet), SCTS 26-09-13 12:41:05 +12 ceyrek,… (+11 more)

### Community 85 - "x-topics"
Cohesion: 0.10
Nodes (21): icerik, periyot, qos, retain, icerik, periyot, qos, retain (+13 more)

### Community 86 - "mockSeries.ts"
Cohesion: 0.22
Nodes (19): bucketStarts(), CONDENSE, connPointValue(), dailyHumidity(), dailyLoad(), elecValue(), envValue(), fnv1a() (+11 more)

### Community 87 - "IngestPipeline"
Cohesion: 0.18
Nodes (8): Tek transaction: telemetri satirlari + son durum + karantina. - Bilinmeyen pano…, IngestPipeline, Son 60 s'de alinan mesaj hizi (reddedilenler dahil: broker'dan gelen yuk)., Kuyrugu partiler halinde yazar. True = kuyruk bosaldi. False = gecici depolama…, Semadan gecmis, zaman damgasi ayristirilmis tek telemetri mesaji., Karantinaya giden mesaj: dusurulmez, nedeniyle birlikte saklanir., Rejection, Sample

### Community 88 - "ExceptionCode"
Cohesion: 0.17
Nodes (20): ExceptionCode, IntEnum, exception_code(), Alarm yoneticisi yuklenmeden alarm bitleri 0 okunursa SCADA 'alarm yok' sanar:…, Harita statiktir: hedefin verisi olmasa da gecersiz adres 0x02'dir (0x0B degil)., test_ack_before_alarm_state_is_loaded_is_target_failed(), test_address_check_comes_before_unit_data(), test_address_outside_blocks_is_illegal_address() (+12 more)

### Community 89 - "risk"
Cohesion: 0.10
Nodes (20): type, additionalProperties, description, type, description, type, contributions, mode (+12 more)

### Community 90 - "gen_grafana_dashboards.py"
Cohesion: 0.26
Nodes (17): alarm_kpi(), build(), dashboard(), Layout, main(), olcek(), series(), _panel() (+9 more)

### Community 91 - "PointValue"
Cohesion: 0.12
Nodes (8): PointValue, datetime, Protocol, StationSource, loop(), fixture, Iki istasyon (ortak adres 1 ve 2); deger listesi test icinde degistirilir., Stations

### Community 92 - "panoalgo/tests/conftest.py"
Cohesion: 0.15
Nodes (17): Ortak test donatilari. Sozlesmeler repodaki `contracts/` dizininden okunur —…, alarm_codes(), assert_valid_labels(), assert_valid_telemetry(), check(), label_schema(), fixture, contracts/alarm-codes.yaml tamami. (+9 more)

### Community 93 - "test_db_integration.py"
Cohesion: 0.22
Nodes (18): db(), ingest(), make_payload(), pano_id(), fixture, TB1 — PgStore'un gercek PostgreSQL/TimescaleDB'ye karsi davranisi. Yigin…, DB yokken API 503 donebilsin ve ingest veriyi tekrar denemek uzere tutabilsin., store() (+10 more)

### Community 94 - "prognostics.py"
Cohesion: 0.15
Nodes (16): backtest(), _median(), Prediction, PrognosisResult, Prognoz geri testi (F-04, Kisi A): tahmin edilen kalan omur -> olculmus…, Bir yorungenin prognoz geri testi., Kalan omur araligina gore koni icinde kalma orani ve medyan tahmin/gercek.…, Tum olcutleri tek sonuca toplar. Tahmin yoksa None (olcum yapilamaz). (+8 more)

### Community 95 - "StreamHub"
Cohesion: 0.16
Nodes (11): Any, WS /api/v1/stream — sunucudan istemciye tek yonlu canli akis (openapi.yaml…, Olay dongusu icinden cagrilir., Herhangi bir thread'den cagrilabilir., _send_updates(), stream(), StreamHub, _wait_for_disconnect() (+3 more)

### Community 96 - "pdu.py"
Cohesion: 0.18
Nodes (17): _concat_info(), _decode_address(), _decode_timestamp(), _decode_user_data(), _encode_address(), encode_deliver(), _encode_timestamp(), _gsm7_user_data() (+9 more)

### Community 97 - "test_sms_modem.py"
Cohesion: 0.14
Nodes (14): log_path(), modem(), fixture, TB2 Adim 5 — uretim SMS surucusu (app.notify.sms_modem) + sanal GSM modem…, Gercek modem gibi: AT+CMGS uzunlugu tutmazsa +CMS ERROR 304 (surucu hesabini…, Onceki oturum AT+CMGS yazip PDU'yu yazamadan koptu: modem hala '> ' isteminde…, sent_pdus(), server() (+6 more)

### Community 98 - "Store"
Cohesion: 0.12
Nodes (9): Protocol, `since` sonrasi olusan her alarm icin telefona (sms/whatsapp) ILK basarili…, Tek transaction, verilen sirayla: yeni olaylar -> alarm satirlari (upsert) ->…, Temizlenmemis tum alarmlar (yeniden baslatmada alarm yoneticisine geri…, En yeni once (raised_at, esitlikte id)., Alarm kimligini tek yazici alarm yoneticisi verir: acilista max(id) + 1., Bildirim denetim izi (KVKK): kanal, maskeli alici, zaman, sonuc., `since` ve sonrasinda olusan (raised_at, olay zamani) alarmlarin oncelik basina… (+1 more)

### Community 99 - "Notifier"
Cohesion: 0.18
Nodes (7): normalize_msisdn(), Notifier, datetime, Alarm servisi dinleyicisi: yalnizca is kuyruguna ekler, beklemez., Vadesi gelen isleri bir kez gonderir, ardindan gelen SMS yanitlarini `wait_s`…, Karsilastirma icin: yalnizca rakamlar, ulusal 0 onekli Turkiye numarasi 90 ile., Sms

### Community 100 - "properties"
Cohesion: 0.12
Nodes (17): description, type, additionalProperties, description, properties, type, description, type (+9 more)

### Community 101 - "001_schema.sql"
Cohesion: 0.19
Nodes (14): alarms, alarms_pano_idx, alarms_state_prio_idx, events, events_pano_time_idx, notifications, panels, quarantine (+6 more)

### Community 102 - "compilerOptions"
Cohesion: 0.12
Nodes (16): compilerOptions, isolatedModules, jsx, lib, module, moduleResolution, noEmit, noFallthroughCasesInSwitch (+8 more)

### Community 103 - "test_detect.py"
Cohesion: 0.22
Nodes (16): phase_compare(), Akimla duzeltilmis faz karsilastirmasi (rapor 6.5 L1-3). r_i = dT_i / I_i^2…, _points(), Sinira kalan sure ve faz karsilastirmasi testleri — PLAN.md TA2 Adim 6.…, Ayni akim, ayni artis -> hicbir nokta one cikmaz., L2 iki kat sicak, akimlar esit -> r_L2 / medyan = 2., EN ONEMLI TEST (rapor 6.5 L1-3): L1 iki kat akim tasiyorsa dT'si dort kat olur…, DSYA1 ile GIRIS ayni gruba girmez; her cikis kendi icinde kiyaslanir. (+8 more)

### Community 104 - "dew_point"
Cohesion: 0.17
Nodes (15): dew_point(), dew_point_margin(), Fiziksel donusumler. Kaynak: HACKATHON_ANALIZ_RAPORU.md 15.1., Magnus formuluyle ciy noktasi (degC). gamma = ln(RH/100) + b*T/(c+T); Td =…, Yuzey sicakligi ile ciy noktasi arasindaki marj (K). Negatif = yogusma., parametrize, Ciy noktasi (Magnus) testleri — PLAN.md TA1 Adim 1. Referans degerler…, Rapor 15.1 tablosundaki dort referans deger. (+7 more)

### Community 105 - "make_rig"
Cohesion: 0.15
Nodes (14): loop(), make_rig(), make(), fixture, ModbusTcpClient, 10.000 panoluk filoda ilk periyot: birim atamasi pano basina degil parti basina…, IEC 104 istasyonu ayni goruntuyu kullanir: eslenmemis birim KeyError, verisi…, Rig (+6 more)

### Community 106 - "properties"
Cohesion: 0.12
Nodes (16): description, type, exclusiveMinimum, type, enum, type, properties, data_file (+8 more)

### Community 107 - "properties"
Cohesion: 0.12
Nodes (16): properties, description, type, description, type, params, point, severity (+8 more)

### Community 108 - "time_to_limit"
Cohesion: 0.16
Nodes (15): 70 K sinirina tahmini kalan saat (rapor 15.1). K(t) ~ K_simdi + Kdot * t…, time_to_limit(), _flat_profile(), Uyarim yoksa K guncellenmez, dolayisiyla egim guvenilmez (rapor 15.1 uyarisi)., K = 2.0e-4, Kdot = 1.0e-5 / saat, I^2 = 250000, sinir 70 K. dT(t) = (2.0e-4 +…, Kdot <= 0 ise sinir asilmaz; sema ttl_h icin null bekliyor ('tahmin yok')., Cok yavas buyume 'yuz yil sonra' gibi anlamsiz bir sayi uretmemeli., Sinir zaten asilmissa 'kalan sure' sifirdir, negatif degil. (+7 more)

### Community 109 - "DeviceReader"
Cohesion: 0.17
Nodes (9): DeviceReader, ModbusReadError, ModbusTcpClient, RuntimeError, Iki cihaz simulatorunden okuyan Modbus master dongusu., Kilavuz: 32-bit olcum iki register, word_order high_first., MPR-53CS'ten faz/notr akimlari ve akim THD'si (gercek register adresleri)., TVOC-2'den sistem durumu ve trip sayaci; cevap yoksa comm_ok=False. (+1 more)

### Community 110 - "test_alarm_store.py"
Cohesion: 0.22
Nodes (13): db(), manager(), pano_id(), fixture, raise_k_warn(), TB2 — alarm kaliciligi: PgStore'un gercek PostgreSQL/TimescaleDB'ye karsi…, store(), test_list_alarms_filters_by_state_priority_and_panel_newest_first() (+5 more)

### Community 111 - "Client"
Cohesion: 0.20
Nodes (3): Client, start(), test_stop_closes_open_connections()

### Community 112 - "detect.py"
Cohesion: 0.24
Nodes (12): default_contracts_dir(), load_thresholds(), Path, L1 fizik tabanli tespit (TA2, Kisi A): K indeksi kestirimi ve faz…, contracts/alarm-codes.yaml thresholds blogu. Dizin basina bir kez okunur…, _repo_contracts_dir(), _thresholds(), default_output() (+4 more)

### Community 113 - "test_loadtest_storage.py"
Cohesion: 0.14
Nodes (13): fixture, TB3 Adim 6 — loadtest/storage.py veri butcesi hesaplari (olcum docs/09'da).…, 1000 baytlik yuk, 25 karakterlik topic: 1 + 2 + 2 + 25 + 2 + 1000 = 1032., Kalan uzunluk 16384 ve ustunde 3 bayttir: 1 + 3 + 2 + 25 + 2 + 20000 = 20033., 30 gun / 10 s = 259.200 mesaj x 1032 B = 267,4944 MB., Gunde 1.000.000 satir; 7 gun sikistirmasiz (100 B), 83 gun sikistirilmis (10…, Kalan uzunluk 16383 -> 2 bayt, 16384 -> 3 bayt (25 karakterlik topic: kalan =…, storage() (+5 more)

### Community 114 - ".__init__"
Cohesion: 0.18
Nodes (11): CONTRACTS_DIR ortam degiskeni, yoksa repo icindeki contracts/ dizini., contract_point_names(), default_contracts_dir(), _pano_id_pattern(), _point_names(), datetime, Path, ProfileKind (+3 more)

### Community 115 - "Tvoc2Block"
Cohesion: 0.18
Nodes (9): ModbusServerContext, build_context(), main(), ModbusSparseDataBlock, ABB TVOC-2 Modbus simulatoru (TA3 Adim 1, Kisi A). Cihazin GERCEK register…, Register okumalarini canli cihaz modeline yonlendirir. Tanimsiz adres icin…, ID 248 ise HICBIR slave kaydedilmez -> sunucu sessiz kalir. Sessizlik iki…, _trip_after() (+1 more)

### Community 116 - "LoopThread"
Cohesion: 0.15
Nodes (5): LoopThread, Arka plan thread'inde calisan asyncio dongusu: sunucular gercek TCP'de, testler…, EdgeCommands, FakeMonotonic, Kenara komut kanalinin test cifti: gonderilenleri kaydeder; accept=False…

### Community 117 - "_ortak.sh"
Cohesion: 0.24
Nodes (11): docker_senaryo_hazir_mi(), host_senaryo_hazir_mi(), python_bul(), PYTHONPATH, renk_hata(), renk_ok(), renk_uyari(), senaryo_engelli_uyarisi() (+3 more)

### Community 118 - "MprBlock"
Cohesion: 0.18
Nodes (8): _feed_from_generator(), main(), MprBlock, ModbusSparseDataBlock, ENTES MPR-53CS Modbus simulatoru (TA3 Adim 2, Kisi A). Cihazin GERCEK register…, Register okumalarini canli cihaz modeline yonlendirir., Enerji sayaclari ve min/max gercek cihazda yazilabilir (sifirlama), ama bizim…, Analizoru panoalgo uretecinin akimlariyla besler (panosim ile ayni fizik).

### Community 119 - "RateMeter"
Cohesion: 0.20
Nodes (7): Pattern, gridup/pano/{pano_id}/tel' -> pano_id grubunu yakalayan tam eslesme deseni., topic_regex(), RateMeter, Son `window_s` saniyedeki olay hizi (1 s kovalari); /fleet/kpi…, /fleet/kpi ingest_msgs_per_s: son 60 s'de alinan mesaj / 60 (1 s kovalari,…, test_rate_meter_averages_the_last_window()

### Community 120 - "panoalgo/tests/helpers.py"
Cohesion: 0.20
Nodes (11): Testlerde tekrar eden kucuk yardimcilar (conftest'ten import etmek yerine)., lag1_autocorr(), mean(), datetime, Kisa UTC zaman damgasi kurucusu: utc(2026, 9, 16, 20)., Lag-1 ornek otokorelasyonu r1 = sum((x[k]-m)(x[k+1]-m)) / sum((x[k]-m)^2).…, utc(), PLAN.md TA1 Adim 6c: lag-1 > 0.9. Verilen Excel'de bu deger 0,00 (rapor 3.4a). (+3 more)

### Community 121 - "test_gen_modbus_doc.py"
Cohesion: 0.18
Nodes (7): gen(), fixture, TB3 Adim 3 — scripts/gen_modbus_doc.py: contracts/modbus-map.yaml -> docs/03 +…, Sozlesme degisip dokuman yeniden uretilmediyse (kural 10 ihlali) burada patlar., regmap(), test_committed_doc_and_csv_are_up_to_date(), test_render_fills_marked_blocks_and_keeps_narrative()

### Community 122 - "pano_dew_point"
Cohesion: 0.21
Nodes (4): pano_real_t, pano_dew_point(), pano_dew_point_margin(), main()

### Community 123 - "RingBuffer"
Cohesion: 0.17
Nodes (7): Broker yokken mesajlari bekletir; dolunca EN ESKIyi dusurur ve sayar., Bekleyenleri sirayla gonderir; ilk basarisizlikta durur ve kalani tutar., RingBuffer, Broker yoksa hicbir sey kaybolmaz; sira bozulmaz., test_the_ring_buffer_drops_the_oldest_and_counts_it(), test_the_ring_buffer_keeps_everything_when_sending_fails(), test_the_ring_buffer_stops_at_the_first_failure_and_keeps_the_rest()

### Community 124 - "test_gen_iec104_doc.py"
Cohesion: 0.18
Nodes (7): gen(), fixture, TB3 Adim 8 (Could) — scripts/gen_iec104_doc.py: IEC 104 nokta plani sozlesme +…, Birlikte calisabilirlik listesinin (§7) alan uzunluklari sabitten degil,…, GK6: kontrol ASDU'lari, sayac sorgulamasi ve dosya transferi standardin…, test_interop_field_widths_and_apdu_limits_are_measured_from_the_codec(), test_interop_marks_control_asdus_and_absent_functions_as_unsupported()

### Community 125 - "items"
Cohesion: 0.18
Nodes (11): additionalProperties, required, type, description, items, type, description, items (+3 more)

### Community 126 - "pano_limits_evaluate"
Cohesion: 0.47
Nodes (10): pano_limits_t, pano_real_t, pano_sample_t, electrical_bits(), environment_bits(), pano_limits_evaluate(), phase_bits(), phases_similarly_loaded() (+2 more)

### Community 127 - "in_alpha_band"
Cohesion: 0.22
Nodes (11): alpha_band(), in_alpha_band(), [(1-a)RUL*, (1+a)RUL*] konisi., Tahmin koninin icinde mi (sinirlar DAHIL)., parametrize, RUL* <= 0'da oran tanimsizdir; sessizce 0 donmek olcumu yalanlar., test_alpha_band_is_symmetric_around_the_true_remaining_life(), test_alpha_band_rejects_a_non_positive_remaining_life() (+3 more)

### Community 128 - "vectors.py"
Cohesion: 0.27
Nodes (10): build_vectors(), default_path(), _inputs(), main(), Path, Ortak test vektoru ureteci (TA3 Adim 3, Kisi A). PLAN.md TA3 Adim 3:…, Isil modelden deterministik (akim, sicaklik artisi) cifti uretir. Gurultu yok:…, Girdi ciftlerini ve Python kestirimcisinin adim adim ciktisini uretir. (+2 more)

### Community 129 - "_feed"
Cohesion: 0.20
Nodes (11): _feed(), _light_profile(), Saglikli baglantida K sabittir; ttl_h null olmali (sahte aciliyet uretme)., ttl'nin butun amaci 70 K'dan ONCE uyarmak. Hafif yukte (300 A) K uc katina…, Bozulma hizlandikca kalan sure kisalmali — is emrinin aciliyeti buradan gelir., expected_i2 verilmezse tahmin yapilamaz; uydurmak yerine null., Isil modelden deterministik (akim, artis) cifti uretip kestirimciyi besler., test_estimator_reports_no_time_to_limit_for_a_stable_connection() (+3 more)

### Community 130 - "test_compression.py"
Cohesion: 0.31
Nodes (7): db(), ingest(), pano_id(), fixture, TB3 Adim 6 — telemetri sikistirmasi (deploy/initdb/005_compression.sql) gercek…, store(), test_writes_and_series_work_on_a_compressed_chunk()

### Community 131 - "acked_codes"
Cohesion: 0.25
Nodes (9): acked_codes(), parametrize, Rafa alinmis alarm da onaylanabilir (alarm_manager.ack ile ayni kural)., test_ack_all_with_password_in_same_request(), test_ack_includes_shelved_alarms(), test_ack_value_zero_is_no_op(), test_edge_command_without_channel_is_target_failed_and_nothing_runs(), test_invalid_command_value_rejects_whole_request() (+1 more)

### Community 132 - "mqtt-telemetry.schema.json"
Cohesion: 0.22
Nodes (8): additionalProperties, description, $id, required, $schema, title, type, x-notes

### Community 133 - "scenario-labels.schema.json"
Cohesion: 0.22
Nodes (8): additionalProperties, description, $id, required, $schema, title, type, x-purpose

### Community 135 - "GatewayStations"
Cohesion: 0.29
Nodes (3): GatewayStations, datetime, IEC 104 istasyon kaynagi: ortak adres = Modbus birimi; degerler ag gecidinin…

### Community 136 - "PromptCheckingPort"
Cohesion: 0.25
Nodes (3): PromptCheckingPort, pyserial port cifti: AT+CMGS'e '> ' istemiyle yanit verir, istem OKUNMADAN…, test_pdu_is_written_only_after_the_prompt_has_been_read()

### Community 137 - "t_conn"
Cohesion: 0.25
Nodes (8): additionalProperties, required, t_conn, description, items, maxItems, minItems, type

### Community 138 - "main"
Cohesion: 0.36
Nodes (7): pano_limits_t, pano_sample_t, contract_limits(), expect(), healthy_sample(), main(), pano_point_t

### Community 139 - "predictions_from_series"
Cohesion: 0.25
Nodes (8): predictions_from_series(), (t_EOL oncesi tahminler, t_EOL sonrasi tahmin sayisi). t_EOL'den SONRA gelen…, _prognosis(), (prognoz geri testi, prognoz yanlis-alarm sayisi, bunlarin alarma donen…, Ihlalden sonra gercek kalan omur negatiftir; oran tanimsiz, sayim anlamli., test_predictions_after_the_breach_are_counted_but_not_scored(), test_series_of_different_lengths_is_rejected(), test_series_skips_samples_without_a_prediction()

### Community 140 - "test_k_index.py"
Cohesion: 0.29
Nodes (7): K indeksi (RLS) testleri — PLAN.md TA2 Adim 1. Beklenen degerlerin kaynagi: -…, Isil modelden sentetik (akim, sicaklik artisi) cifti uretir., Gevseyen baglantida K/K0 yukselir; tau makul araliktadir., Yuk sabitse RLS guncellenmez (kalici uyarim kosulu)., _simulate(), test_k_index_not_updated_without_excitation(), test_k_index_tracks_degradation()

### Community 141 - "duman-testi.sh"
Cohesion: 0.32
Nodes (3): baslik(), kontrol(), duman-testi.sh script

### Community 142 - "main"
Cohesion: 0.52
Nodes (6): pano_limits_t, default_limits(), main(), median_of(), point_current(), point_topology()

### Community 143 - "format_pano_id"
Cohesion: 0.29
Nodes (7): format_pano_id(), Sozlesme desenine uyan pano kimligi: format_pano_id("adm", 1) -> "ADM-00001"., parametrize, Sema ^[A-Z]{3}-[0-9]{5}$ — 'ADM-1' degil 'ADM-00001'., test_pano_id_is_zero_padded_to_the_contract_pattern(), test_pano_id_prefix_is_upper_cased(), test_pano_id_rejects_values_the_contract_cannot_express()

### Community 144 - "alpha_lambda"
Cohesion: 0.29
Nodes (7): alpha_lambda(), AlphaLambdaPoint, Her lambda icin o ana EN YAKIN tahmini degerlendirir. lambda, ilk tahmin ile…, Belirli bir lambda anindaki alfa-lambda sonucu., test_alpha_lambda_marks_a_point_outside_the_cone(), test_alpha_lambda_of_an_empty_series_is_empty(), test_alpha_lambda_reports_one_point_per_requested_fraction()

### Community 145 - "relative_accuracy"
Cohesion: 0.29
Nodes (7): RA = 1 - |RUL* - RUL^| / RUL*. KIRPILMAZ: literaturde bazi uygulamalar negatif…, relative_accuracy(), Kirpma, iki kat hata ile yirmi kat hatayi ayni gosterirdi (modul notu)., test_relative_accuracy_is_one_for_an_exact_prediction(), test_relative_accuracy_is_zero_when_the_error_equals_the_true_life(), test_relative_accuracy_rejects_a_non_positive_remaining_life(), test_relative_accuracy_stays_negative_and_is_not_clipped()

### Community 146 - "gen_alarm_doc.py"
Cohesion: 0.48
Nodes (6): alarm_catalog(), main(), priority_matrix(), docs/06-alarm-matrisi.md icindeki URETILMIS tablolari contracts/alarm-…, render(), _yes()

### Community 147 - ".add_listener"
Cohesion: 0.33
Nodes (4): Degisiklik dinleyicisi. `digest` metodu olan dinleyici (bildirim ag gecidi)…, Gunluk ozet (DIGEST_AT) dinleyicisi; AYNI dinleyici iki kez kaydedilmez.…, ChangeListener, DigestListener

### Community 148 - "expect"
Cohesion: 0.33
Nodes (6): description, items, minItems, type, pattern, expect

### Community 149 - "thermal.c"
Cohesion: 0.47
Nodes (4): pano_real_t, pano_thermal_a(), pano_thermal_steady(), pano_thermal_step()

### Community 150 - "parse_units"
Cohesion: 0.40
Nodes (5): parse_units(), Pattern, MODBUS_UNITS: '1=ADM-00001, 2=GDZ-00123' -> {1: 'ADM-00001', 2: 'GDZ-00123'};…, test_parse_units(), test_parse_units_rejects_invalid()

### Community 151 - "alarms"
Cohesion: 0.40
Nodes (5): description, items, type, pattern, alarms

### Community 152 - ".record_trip"
Cohesion: 0.40
Nodes (4): datetime, Yeni ark tripi: log basa eklenir, sayac artar, 1300 bit0 set edilir., Bir trip kaydi (kilavuz 4.4.1)., Tvoc2Trip

### Community 154 - "l0_breach_at"
Cohesion: 0.50
Nodes (4): description, format, type, l0_breach_at

### Community 155 - "scenario_id"
Cohesion: 0.50
Nodes (4): scenario_id, description, enum, type

### Community 156 - ".__init__"
Cohesion: 0.50
Nodes (3): Path, ProfileKind, period_s verilirse ornekleme periyodu zaman damgalarindan TURETILMEZ. Kenar…

### Community 157 - "UnknownTypeError"
Cohesion: 0.67
Nodes (3): ValueError, Bu istasyonun cozmedigi tip; sunucu ASDU'yu COT 44 ile geri doner., UnknownTypeError

### Community 158 - "generated_at"
Cohesion: 0.67
Nodes (3): format, type, generated_at

### Community 159 - "pano_id"
Cohesion: 0.67
Nodes (3): pattern, type, pano_id

### Community 160 - "pano_type"
Cohesion: 0.67
Nodes (3): default, type, pano_type

### Community 161 - "seed"
Cohesion: 0.67
Nodes (3): seed, description, type

### Community 162 - "t_start"
Cohesion: 0.67
Nodes (3): t_start, format, type

## Knowledge Gaps
- **367 isolated node(s):** `HistorySample`, `Toggles`, `ImportMeta`, `ImportMetaEnv`, `ChartSeries` (+362 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1533 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **25 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PanelSimulator` connect `PanelSimulator` to `test_profiles.py`, `scenarios.py`, `test_generator.py`, `fleet.py`, `EdgePipeline`, `panosim.py`, `run`, `.__init__`, `MprBlock`, `panoalgo/tests/conftest.py`?**
  _High betweenness centrality (0.074) - this node is a cross-community bridge._
- **Why does `Contracts` connect `Contracts` to `fleet.py`, `views.py`, `Alarm`, `ScadaGateway`, `dispatcher.py`, `seed_demo.py`, `RiskEngine`, `test_iec104_points.py`, `alarm_service.py`, `main.py`, `encoder.py`, `ingest.py`, `MqttSubscriber`, `AlarmManager`, `backend/tests/helpers.py`, `IngestPipeline`, `gen_grafana_dashboards.py`, `Notifier`, `RateMeter`?**
  _High betweenness centrality (0.068) - this node is a cross-community bridge._
- **Why does `PhysicsPayloadFactory` connect `fleet.py` to `Contracts`, `PanelSimulator`?**
  _High betweenness centrality (0.057) - this node is a cross-community bridge._
- **Are the 12 inferred relationships involving `MemoryStore` (e.g. with `StoreError` and `EventRecord`) actually correct?**
  _`MemoryStore` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `PanelSimulator` (e.g. with `Ar1Noise` and `_inject()`) actually correct?**
  _`PanelSimulator` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `Alarm` (e.g. with `AlarmService` and `_digest_summary()`) actually correct?**
  _`Alarm` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 30 inferred relationships involving `Contracts` (e.g. with `AlarmManager` and `AlarmService`) actually correct?**
  _`Contracts` has 30 INFERRED edges - model-reasoned connections that need verification._