export const WIDGET_SRC = "https://YOUR_WIDGET_HOST/cortexa-widget.js";

export interface Guide {
  id: string;
  label: string;
  steps: string[];
  code: string;
  filename?: string;
  note?: string;
}

export function getGuides(key: string): Guide[] {
  const tag = `<script src="${WIDGET_SRC}" data-widget-key="${key}" async></script>`;

  return [
    {
      id: "html",
      label: "HTML",
      steps: [
        "Open the HTML file for each page where the chat should appear (or your shared layout file).",
        "Paste the snippet just before the closing </body> tag.",
        "Save, deploy and reload the page.",
      ],
      code: tag,
      filename: "index.html",
    },
    {
      id: "php",
      label: "PHP",
      steps: [
        "Create a partial file that holds the script tag.",
        "Include that partial once from your shared footer, so every page loads the widget a single time.",
        "Do not paste the script into individual pages as well, or the widget loads twice.",
      ],
      code: `<?php /* partials/cortexa-widget.php */ ?>
${tag}

<?php /* footer.php, before the closing body tag */ ?>
<?php include __DIR__ . '/partials/cortexa-widget.php'; ?>
</body>
</html>`,
      filename: "footer.php",
    },
    {
      id: "wordpress",
      label: "WordPress",
      steps: [
        "Easiest: install a header/footer scripts plugin, paste the snippet into its Footer box and save.",
        "Alternative: in a child theme, add the snippet to footer.php just before the wp_footer() call.",
        "Avoid editing a parent theme directly, because theme updates will overwrite your change.",
      ],
      code: tag,
      note: "Plugin and menu names vary between WordPress versions and plugins.",
    },
    {
      id: "react",
      label: "React",
      steps: [
        "Create this component and render it once near the root of your app (for example in App.tsx).",
        "It loads the widget script a single time and removes it when the component unmounts.",
      ],
      code: `import { useEffect } from "react";

export default function CortexaWidget() {
  useEffect(() => {
    if (document.getElementById("cortexa-widget")) return;
    const script = document.createElement("script");
    script.id = "cortexa-widget";
    script.src = "${WIDGET_SRC}";
    script.async = true;
    script.dataset.widgetKey = "${key}";
    document.body.appendChild(script);
    return () => {
      script.remove();
    };
  }, []);

  return null;
}`,
      filename: "CortexaWidget.tsx",
    },
    {
      id: "nextjs",
      label: "Next.js",
      steps: [
        "Open your root layout (app/layout.tsx for the App Router).",
        "Import next/script and render the Script element once, inside the body.",
      ],
      code: `import Script from "next/script";

// inside <body> in app/layout.tsx
<Script
  src="${WIDGET_SRC}"
  data-widget-key="${key}"
  strategy="afterInteractive"
/>`,
      filename: "app/layout.tsx",
    },
    {
      id: "shopify",
      label: "Shopify",
      steps: [
        "In your Shopify admin, open Online Store, then Themes, and choose Edit code on your live or a duplicated theme.",
        "Open layout/theme.liquid and paste the snippet just before the closing </body> tag.",
        "Save and check your storefront.",
      ],
      code: tag,
      filename: "layout/theme.liquid",
      note: "Duplicate the theme first so you can roll back. Menu names may change.",
    },
    {
      id: "wix",
      label: "Wix",
      steps: [
        "Open your site's Settings and find Custom Code.",
        "Add new code, paste the snippet, and apply it to All pages.",
        "Place it in the Body - end position, then save and publish.",
      ],
      code: tag,
      note: "Custom code may require a paid plan with a connected domain.",
    },
    {
      id: "squarespace",
      label: "Squarespace",
      steps: [
        "Open Settings, then Advanced, then Code Injection.",
        "Paste the snippet into the Footer box and save.",
      ],
      code: tag,
      note: "Code injection may be limited by plan, and the menu path can change.",
    },
    {
      id: "gtm",
      label: "Google Tag Manager",
      steps: [
        "In your container, create a new tag and choose the Custom HTML type.",
        "Paste the snippet, then set the trigger to All Pages.",
        "Preview in Tag Manager's debug mode, then publish the container.",
      ],
      code: tag,
      note: "Ad blockers and consent tools can stop tags from firing. Test with your consent setup.",
    },
  ];
}