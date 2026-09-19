import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { authHeader, clearToken, getToken, onTokenChange, setToken } from "./session";

/**
 * F-19 — istemci tarafinda belirtec deposu.
 *
 * SINIR: bu dosya "node" ortaminda kosar (vite.config.ts) ve `sessionStorage` ile
 * `localStorage` asagida bellek ici TAKLITLERLE saglanir. Taklit, gercek tarayici
 * davranisinin yerine gecmez; olculen sey session.ts'in DOGRU DEPOYU secip secmedigi ve
 * depo patladiginda cagirani kirip kirmadigidir.
 *
 * 19 Eylul duzeltmesi: bu yorum eskiden "depoda jsdom yok; yeni npm bagimliligi yasak"
 * diyordu — K7/7.1 ile ikisi de yanlis oldu (jsdom kurulu). Dosyanin node'da KALMASI
 * yine de bilincli ve OLCULMUS bir karardir: global `environment: "jsdom"` denendiginde
 * 12 dosyanin 3'u kirildi (38 test) ve sure 1,95 s'den 40,02 s'ye cikti; gerekce
 * vite.config.ts'te yazili. Ayrica asagidaki `Object.assign(globalThis, ...)` deseni
 * jsdom'da Window uzerindeki salt-okunur erisimcilere carpma riski tasir — bellek ici
 * taklit, olculmek istenen seyi (depo secimi) daha dar ve daha kesin sinar.
 *
 * Asil kilit: "yalnizca sessionStorage kullanir". localStorage'a kaymasi, kontrol
 * odasindaki paylasilan bir makinede belirtecin sonraki vardiyada da durmasi demekti.
 */

const KEY = "gridup.operator.token";

function memoryStorage(failing = false) {
  const data = new Map<string, string>();
  return {
    get length() {
      return data.size;
    },
    getItem(key: string) {
      if (failing) throw new Error("depolama kapali");
      return data.has(key) ? data.get(key)! : null;
    },
    setItem(key: string, value: string) {
      if (failing) throw new Error("depolama kapali");
      data.set(key, value);
    },
    removeItem(key: string) {
      if (failing) throw new Error("depolama kapali");
      data.delete(key);
    },
    clear() {
      data.clear();
    },
  };
}

function install(session: ReturnType<typeof memoryStorage>, local = memoryStorage()) {
  Object.assign(globalThis, { sessionStorage: session, localStorage: local });
  return local;
}

let local: ReturnType<typeof memoryStorage>;

beforeEach(() => {
  local = install(memoryStorage());
});

afterEach(() => {
  Reflect.deleteProperty(globalThis, "sessionStorage");
  Reflect.deleteProperty(globalThis, "localStorage");
});

describe("belirtec deposu", () => {
  it("yazilan belirtec geri okunur", () => {
    setToken("s3cret");
    expect(getToken()).toBe("s3cret");
  });

  it("temizlenince null doner", () => {
    setToken("s3cret");
    clearToken();
    expect(getToken()).toBeNull();
  });

  it("yalnizca sessionStorage kullanir, localStorage'a DOKUNMAZ", () => {
    setToken("s3cret");
    expect(sessionStorage.getItem(KEY)).toBe("s3cret");
    expect(local.length).toBe(0);
  });

  it("depolama patlarsa null doner ve cagiran kirilmaz", () => {
    // Gizli sekme veya depolama kapali: erisim throw edebilir. Kimlik dogrulama
    // kapaliysa yigin belirtecsiz de calisir, o yuzden burada patlamak yanlis olurdu.
    install(memoryStorage(true));
    expect(getToken()).toBeNull();
    expect(() => setToken("s3cret")).not.toThrow();
    expect(() => clearToken()).not.toThrow();
    expect(authHeader()).toEqual({});
  });
});

describe("authHeader", () => {
  it("belirtec varsa Bearer basligi uretir", () => {
    setToken("s3cret");
    expect(authHeader()).toEqual({ Authorization: "Bearer s3cret" });
  });

  it("belirtec yoksa BOS nesne doner", () => {
    // Bos dize ile "Bearer " gondermek sunucuda 401 uretirdi; hic gondermemek dogru.
    expect(authHeader()).toEqual({});
  });
});

describe("onTokenChange", () => {
  it("yazma ve silmede haber verir, abonelik birakilinca susar", () => {
    const seen: Array<string | null> = [];
    const unsubscribe = onTokenChange(() => seen.push(getToken()));

    setToken("a");
    clearToken();
    unsubscribe();
    setToken("b");

    expect(seen).toEqual(["a", null]);
  });

  it("depolama patlasa bile haber verir", () => {
    // Arayuz yine tazelenmeli: kullanici "giris yapildi" gormeli ya da gormemeli,
    // sessizce eski halinde donup kalmamali.
    install(memoryStorage(true));
    let calls = 0;
    const unsubscribe = onTokenChange(() => calls++);
    setToken("a");
    unsubscribe();
    expect(calls).toBe(1);
  });
});
