"use client";

// A simple banner to show important messages to the user. It can be used for things like maintenance notifications, new features, etc.
export default function AlertBanner({ message }: { message: string }) {
  return <div className="banner">{message}</div>;
}
