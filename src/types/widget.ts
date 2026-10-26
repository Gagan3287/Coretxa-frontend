export interface WidgetConfig {
  botId: string;
  displayName: string;
  greeting: string;
  color: string;
  position: "right" | "left";
  allowedOrigins: string[];
  widgetKey: string;
  hostedUrl: string;
}