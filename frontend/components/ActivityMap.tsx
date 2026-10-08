import dynamic from "next/dynamic";

const ActivityMapInner = dynamic(
  () => import("./ActivityMapInner").then((m) => ({ default: m.ActivityMapInner })),
  {
    ssr: false,
    loading: () => (
      <div
        className="w-full bg-gray-100 rounded-lg animate-pulse"
        style={{ height: 340 }}
      />
    ),
  }
);

export { ActivityMapInner as ActivityMap };

// Re-export via dynamic for use in pages
export default ActivityMapInner;
