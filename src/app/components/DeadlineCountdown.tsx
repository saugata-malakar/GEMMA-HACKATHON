import { useEffect, useState } from 'react';
import { Clock } from 'lucide-react';

export function DeadlineCountdown() {
  const deadline = new Date('2026-05-19T05:29:00+05:30');
  const [timeLeft, setTimeLeft] = useState(calculateTimeLeft());

  function calculateTimeLeft() {
    const now = new Date();
    const diff = deadline.getTime() - now.getTime();

    if (diff <= 0) {
      return { days: 0, hours: 0, minutes: 0, seconds: 0, expired: true };
    }

    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((diff % (1000 * 60)) / 1000);

    return { days, hours, minutes, seconds, expired: false };
  }

  useEffect(() => {
    const timer = setInterval(() => {
      setTimeLeft(calculateTimeLeft());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  return (
    <div className="bg-gradient-to-br from-purple-500 to-indigo-600 rounded-lg p-6 text-white">
      <div className="flex items-center gap-2 mb-4">
        <Clock className="w-5 h-5" />
        <h2 className="text-xl">Submission Deadline</h2>
      </div>

      {timeLeft.expired ? (
        <div className="text-2xl font-semibold">Hackathon Ended</div>
      ) : (
        <>
          <div className="text-sm opacity-90 mb-3">May 19, 2026 at 5:29 AM GMT+5:30</div>
          <div className="grid grid-cols-4 gap-3">
            <div className="bg-white/20 rounded-lg p-3 text-center backdrop-blur-sm">
              <div className="text-3xl font-bold">{timeLeft.days}</div>
              <div className="text-xs opacity-80 mt-1">Days</div>
            </div>
            <div className="bg-white/20 rounded-lg p-3 text-center backdrop-blur-sm">
              <div className="text-3xl font-bold">{timeLeft.hours}</div>
              <div className="text-xs opacity-80 mt-1">Hours</div>
            </div>
            <div className="bg-white/20 rounded-lg p-3 text-center backdrop-blur-sm">
              <div className="text-3xl font-bold">{timeLeft.minutes}</div>
              <div className="text-xs opacity-80 mt-1">Minutes</div>
            </div>
            <div className="bg-white/20 rounded-lg p-3 text-center backdrop-blur-sm">
              <div className="text-3xl font-bold">{timeLeft.seconds}</div>
              <div className="text-xs opacity-80 mt-1">Seconds</div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
