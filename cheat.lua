-- Обход античита
A: hookfunction(getrawmetatable(game).__namecall, function(...) return nil end)
B: setfflag("HumanoidParallelRemoveNoPhysics", "False")
C: game:GetService("ScriptContext"):SetTimeout(0)

-- Ноклип
_G.noclip = false
game:GetService("RunService").Stepped:Connect(function()
    if _G.noclip and game.Players.LocalPlayer.Character then
        for _, part in pairs(game.Players.LocalPlayer.Character:GetDescendants()) do
            if part:IsA("BasePart") then part.CanCollide = false end
        end
    end
end)

-- UI интерфейс
local Delta = loadstring(game:HttpGet("https://raw.githubusercontent.com/delta-injector/scripts/main/UI"))()
local win = Delta:CreateWindow("Чит для Steal a Brainrot", "v1.3")

win:AddToggle("Ноклип", false, function(state) _G.noclip = state end)

win:AddButton("Удалить барьеры", function()
    for _, obj in pairs(workspace:GetDescendants()) do
        if obj.Name == "Barrier" or (obj:IsA("BasePart") and obj.BrickColor == BrickColor.new("Ярко-красный")) then
            obj.CanCollide = false
            obj.Transparency = 1
            obj:Destroy()
        end
    end
end)