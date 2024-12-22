# Roblox Message Debugging Guide

## 1. Message Tracking System

```lua
-- MessageTracker.lua
local MessageTracker = {}
MessageTracker.__index = MessageTracker

local HttpService = game:GetService("HttpService")

function MessageTracker.new()
    local self = setmetatable({}, MessageTracker)
    self.sentMessages = {}
    self.messageLog = {}
    self.timeWindow = 5  -- 5 second window for duplicate detection
    return self
end

function MessageTracker:generateRequestId()
    return HttpService:GenerateGUID()
end

function MessageTracker:createMessageSignature(npcId, userId, message)
    return string.format("%s:%s:%s", npcId, userId, message)
end

function MessageTracker:logMessage(npcId, userId, message, requestId)
    table.insert(self.messageLog, {
        timestamp = os.time(),
        npc_id = npcId,
        user_id = userId,
        message = message,
        request_id = requestId
    })
    
    -- Keep only last 100 messages
    if #self.messageLog > 100 then
        table.remove(self.messageLog, 1)
    end
end

function MessageTracker:isDuplicate(npcId, userId, message)
    local currentTime = os.time()
    local signature = self:createMessageSignature(npcId, userId, message)
    
    -- Clean old messages
    for key, data in pairs(self.sentMessages) do
        if currentTime - data.timestamp > self.timeWindow then
            self.sentMessages[key] = nil
        end
    end
    
    -- Check for recent duplicate
    if self.sentMessages[signature] then
        warn(string.format(
            "DUPLICATE DETECTED: %s (%.2f seconds since last)",
            signature,
            currentTime - self.sentMessages[signature].timestamp
        ))
        return true
    end
    
    -- Store new message
    self.sentMessages[signature] = {
        timestamp = currentTime,
        request_id = self:generateRequestId()
    }
    return false
end

function MessageTracker:printMessageHistory()
    print("\nMessage History:")
    print("---------------")
    for _, msg in ipairs(self.messageLog) do
        local timeStr = os.date("%H:%M:%S", msg.timestamp)
        print(string.format(
            "[%s] NPC:%s User:%s ReqID:%s\nMessage: %s\n",
            timeStr,
            msg.npc_id,
            msg.user_id,
            msg.request_id,
            msg.message
        ))
    end
end

return MessageTracker
```

## 2. Enhanced Message Sender

```lua
-- MessageSender.lua
local MessageSender = {}
MessageSender.__index = MessageSender

local MessageTracker = require(script.Parent.MessageTracker)
local HttpService = game:GetService("HttpService")

function MessageSender.new(endpoint)
    local self = setmetatable({}, MessageSender)
    self.endpoint = endpoint
    self.tracker = MessageTracker.new()
    self.retryCount = 0
    self.maxRetries = 3
    return self
end

function MessageSender:sendMessage(npcId, userId, message)
    -- Check for duplicates
    if self.tracker:isDuplicate(npcId, userId, message) then
        warn("Duplicate message blocked")
        return
    end
    
    -- Generate request ID
    local requestId = self.tracker:generateRequestId()
    
    -- Create payload
    local payload = {
        npc_id = npcId,
        participant_id = userId,
        message = message,
        request_id = requestId,
        timestamp = os.time()
    }
    
    -- Log attempt
    self.tracker:logMessage(npcId, userId, message, requestId)
    
    -- Send request
    local success, response = pcall(function()
        return HttpService:RequestAsync({
            Url = self.endpoint,
            Method = "POST",
            Headers = {
                ["Content-Type"] = "application/json"
            },
            Body = HttpService:JSONEncode(payload)
        })
    end)
    
    if not success then
        warn("Failed to send message:", response)
        -- Handle retry logic here if needed
    end
    
    return success, response
end

function MessageSender:printHistory()
    self.tracker:printMessageHistory()
end

return MessageSender
```

## 3. Test Script

```lua
-- test_messages.lua
local MessageSender = require(script.Parent.MessageSender)

local function runTest()
    local sender = MessageSender.new("http://localhost:7777/letta/v1/chat/v2")
    
    -- Test 1: Normal sequence
    print("\nTest 1: Normal sequence")
    local messages = {
        "TEST_1: Starting sequence",
        "TEST_2: Checking timing",
        "TEST_3: Almost done"
    }
    
    for _, msg in ipairs(messages) do
        sender:sendMessage(
            "test-npc-123",
            "test-user-456",
            msg
        )
        wait(1)  -- Wait between messages
    end
    
    -- Test 2: Rapid identical messages
    print("\nTest 2: Rapid identical messages")
    local rapidMsg = "DUPLICATE_TEST_ABC_123"
    for i = 1, 3 do
        sender:sendMessage(
            "test-npc-123",
            "test-user-456",
            rapidMsg
        )
        wait(0.1)  -- Very short delay
    end
    
    -- Print history
    print("\nFinal Message History:")
    sender:printHistory()
end

return runTest
```

## 4. Implementation Steps

1. Add these files to your project:
```
/src
  /Chat
    MessageTracker.lua
    MessageSender.lua
    test_messages.lua
```

2. Replace your current message sending code:
```lua
-- Old code:
local function sendMessage(npcId, message)
    -- Your current code
end

-- New code:
local MessageSender = require(path.to.MessageSender)
local sender = MessageSender.new(YOUR_ENDPOINT)

local function sendMessage(npcId, userId, message)
    return sender:sendMessage(npcId, userId, message)
end
```

3. Run tests:
```lua
local runTest = require(path.to.test_messages)
runTest()
```

## 5. Debugging Steps

1. Check message logs:
```lua
sender:printHistory()
```

2. Look for warnings:
```
[Warning] DUPLICATE DETECTED: npc-123:user-456:Hello (0.15 seconds since last)
```

3. Monitor network requests:
   - Enable HTTP request logging in Studio
   - Check Studio Output window
   - Look for multiple requests with same content

4. Common issues to check:
   - Event connections firing multiple times
   - UI button double-clicks
   - Network retry logic
   - Error handling that might retry automatically