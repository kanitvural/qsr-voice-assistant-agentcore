import asyncio
async def child():
    raise ValueError("Child Error")
async def main():
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(child())
    except Exception as e:
        print("Caught by Exception:", type(e))
    except BaseException as e:
        print("Caught by BaseException:", type(e))

asyncio.run(main())
