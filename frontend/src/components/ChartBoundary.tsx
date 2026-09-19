import { Component, Suspense, type ReactNode } from "react";
/** Heavy chart modules load only when a measurement view is actually shown. */
export class ChartBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? (
      <p role="alert" className="chart-empty">
        Grafik modülü yüklenemedi.{" "}
        <button onClick={() => window.location.reload()}>Yeniden yükle</button>
      </p>
    ) : (
      <Suspense
        fallback={
          <div className="chart-loading" role="status">
            Ölçüm grafiği hazırlanıyor…
          </div>
        }
      >
        {this.props.children}
      </Suspense>
    );
  }
}
