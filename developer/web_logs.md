# view stratifyai web ui logs:

## View last 20 lines
tail -20 /tmp/uvicorn.log

## Follow logs in real-time
tail -f /tmp/uvicorn.log

## View all logs
cat /tmp/uvicorn.log

## View logs with less (for scrolling)
less /tmp/uvicorn.log