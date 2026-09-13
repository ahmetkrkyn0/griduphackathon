// Pano Beyni — DIN ray kutusu (parametrik OpenSCAD kaynagi)
// Sahip: Kisi C. Malzeme: V-0 (UL94/IEC 60695-11-10) polikarbonat, sartname 2.2.1.xiii.
// Referans govde: Fibox ARCA 92/125 sinifi (hardware/pano-beyni/bom.csv).
// Konnektorler io-tablosu.md ile birebir (J1-J10); alt kenarda vidali klemens kesikleri,
// ust kenarda anten delikleri (RF + hucresel, sartname 2.2.8.1.iv harici anten cikisi).
//
// NOT (STATUS.md karar #4): bu gelistirme ortaminda `openscad` calistirilamadi (kurulu degil,
// internet erisimi yok); dolayisiyla STL BU TESLIMDE URETILMEDI. Bu dosya OpenSCAD kurulu bir
// makinede `openscad -o din-kutu.stl din-kutu.scad` ile dogrudan STL'e cevrilebilir durumdadir.
// Asagidaki olculer BOM'daki referans govdeyle (Fibox ARCA 92/125) tutarli secilmistir.

/* [Govde olculeri] */
box_width  = 125; // mm, DIN raya paralel (yaklasik 7 DIN modulu)
box_height = 92;  // mm
box_depth  = 60;  // mm, pano ust bolmesindeki derinlige gore (450 mm derinlikli povnun icinde bolluk var)
wall = 2.2;       // mm, V-0 polikarbonat cidar kalinligi

/* [DIN ray klipsi -- EN 50022, 35 mm top-hat ray] */
din_rail_width = 35;
din_rail_depth = 7.5;
din_clip_travel = 4; // yayli klips esneme payi

/* [Konnektor kesikleri (io-tablosu.md J1-J10, alt kenar)] */
conn_w = 8; conn_h = 14; conn_gap = 3;
conn_count = 10;

/* [Anten delikleri (ust kenar)] */
ant_hole_d = 8; // SMA/U.FL gecis deligi

$fn = 48;

module govde_kabuk() {
    difference() {
        cube([box_width, box_depth, box_height]);
        translate([wall, wall, wall])
            cube([box_width - 2*wall, box_depth - 2*wall, box_height - 2*wall + 1]);
    }
}

module din_klips() {
    // Arka yuzeyde, EN 50022 35 mm raya oturan basit yayli klips govdesi.
    translate([box_width/2 - din_rail_width/2 - 3, -3, box_height - 18])
        difference() {
            cube([din_rail_width + 6, din_rail_depth + din_clip_travel + 3, 16]);
            translate([3, din_clip_travel, 2])
                cube([din_rail_width, din_rail_depth + 1, 14]);
        }
}

module alt_konnektor_kesikleri() {
    toplam = conn_count * conn_w + (conn_count - 1) * conn_gap;
    baslangic = (box_width - toplam) / 2;
    for (i = [0 : conn_count - 1])
        translate([baslangic + i * (conn_w + conn_gap), -1, -1])
            cube([conn_w, box_depth + 2, conn_h + 1]);
}

module ust_anten_delikleri() {
    // 2 delik: 802.15.4/BLE (U.FL uzeri kisa pigtail) + hucresel modem SMA.
    translate([box_width * 0.3, box_depth/2, -1])
        cylinder(d = ant_hole_d, h = wall + 2);
    translate([box_width * 0.7, box_depth/2, -1])
        cylinder(d = ant_hole_d, h = wall + 2);
}

module pano_beyni_kutu() {
    difference() {
        union() {
            govde_kabuk();
            din_klips();
        }
        alt_konnektor_kesikleri();
        translate([0, 0, box_height - wall - 1]) ust_anten_delikleri();
    }
}

pano_beyni_kutu();

// Montaj notlari:
// - Kapak (bu dosyada modellenmedi) 4x M3 kilitli vida ile sabitlenir, contali (IP20 dahili).
// - Kart montaj ayaklari kutunun ic tabaninda 4x M2.5 spacer (bu revizyonda eklenmedi).
// - Konformal kaplamali kart, kutunun icine kaydirmali raylarla yerlesir (bkz. blok-diyagrami.md S2).
