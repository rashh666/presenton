import ToolTip from '@/components/ToolTip'
import { Button } from '@/components/ui/button'
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from '@/components/ui/command'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Select, SelectItem, SelectContent, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { cn } from '@/lib/utils'
import { LLMConfig } from '@/types/llm_config'
import OpenAICompatibleImageFields from '@/components/OpenAICompatibleImageFields'
import { DALLE_3_QUALITY_OPTIONS, GPT_IMAGE_1_5_QUALITY_OPTIONS, IMAGE_PROVIDERS } from '@/utils/providerConstants'
import { Check, ChevronUp, Eye, EyeOff } from 'lucide-react'
import React, { useEffect, useState } from 'react'

const ImageProvider = ({ llmConfig, setLlmConfig }: { llmConfig: LLMConfig, setLlmConfig: (config: any) => void }) => {
    const [openImageProviderSelect, setOpenImageProviderSelect] = useState(false);
    const [showApiKey, setShowApiKey] = useState(false);
    const [openaiCompatListMeta, setOpenaiCompatListMeta] = useState<{
        modelsChecked: boolean
        modelCount: number
    }>({ modelsChecked: false, modelCount: 0 })

    useEffect(() => {
        if (llmConfig.IMAGE_PROVIDER !== 'openai_compatible') {
            setOpenaiCompatListMeta({ modelsChecked: false, modelCount: 0 })
        }
    }, [llmConfig.IMAGE_PROVIDER])

    const isImageGenerationDisabled = llmConfig.DISABLE_IMAGE_GENERATION ?? false;
    const handleChangeImageGenerationDisabled = (value: boolean) => {
        setLlmConfig((prev: any) => ({
            ...prev,
            DISABLE_IMAGE_GENERATION: value
        }));
    }
    const input_field_changed = (value: string, field: string) => {
        setLlmConfig((prev: any) => ({
            ...prev,
            [field]: value
        }));
        if (field === 'IMAGE_PROVIDER') {
            setOpenImageProviderSelect(false);
        }
    }

    const getFieldValue = (field?: string) => {
        if (!field) return "";
        return (llmConfig as Record<string, string | undefined>)[field] || "";
    };

    const updateFieldValue = (field: string | undefined, value: string) => {
        if (!field) return;
        setLlmConfig((prev: any) => ({
            ...prev,
            [field]: value,
        }));
    };

    const renderQualitySelector = (llmConfig: LLMConfig, input_field_changed: (value: string, field: string) => void) => {
        if (llmConfig.IMAGE_PROVIDER === "dall-e-3") {
            return (
                <div className="w-[222px] mr-0 ml-auto">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                        DALL·E 3 Image Quality
                    </label>
                    <div className="">
                        <Select value={llmConfig.DALL_E_3_QUALITY || 'standard'} onValueChange={(value) => input_field_changed(value, "DALL_E_3_QUALITY")}>
                            <SelectTrigger className="w-full h-12 px-4 py-4 outline-none border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-colors hover:border-gray-400 justify-between">
                                <SelectValue placeholder="Select a quality" />
                            </SelectTrigger>
                            <SelectContent>
                                {DALLE_3_QUALITY_OPTIONS.map((option) => (
                                    <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>

                    </div>
                </div>
            );
        }

        if (llmConfig.IMAGE_PROVIDER === "gpt-image-1.5") {
            return (
                <div className="w-[222px]">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                        GPT Image 1.5 Quality
                    </label>
                    <div className="">
                        <Select
                            value={llmConfig.GPT_IMAGE_1_5_QUALITY || 'low'}
                            onValueChange={(value) => input_field_changed(value, "GPT_IMAGE_1_5_QUALITY")}
                        >
                            <SelectTrigger

                                className="w-full h-12 px-4 py-4 outline-none border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-colors hover:border-gray-400 justify-between">
                                <SelectValue placeholder="Select a quality" />
                            </SelectTrigger>
                            <SelectContent>
                                {GPT_IMAGE_1_5_QUALITY_OPTIONS.map((option) => (
                                    <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>

                    </div>
                </div>
            );
        }

        return null;
    };

    return (
        <div className="space-y-6 bg-[#F9F8F8] p-7 rounded-[12px] ">
            <div className="mb-4 flex flex-col gap-8 rounded-[12px] bg-white pt-5 pb-10 px-10">
                <div className="flex w-full justify-end">
                    <ToolTip content="Enable/Disable Image Generation" className="flex items-center">
                        <div className="flex justify-end items-center">
                            <Switch
                                checked={!isImageGenerationDisabled}
                                className='data-[state=checked]:bg-[#4791FF] data-[state=unchecked]:bg-gray-400'
                                onCheckedChange={(checked) => handleChangeImageGenerationDisabled(!checked)}
                            />
                        </div>
                    </ToolTip>
                </div>

                <div className="flex flex-col gap-8 lg:flex-row lg:items-end lg:justify-between lg:gap-6">
                    <div className="max-w-[290px] shrink-0">
                        <div className='w-[60px] h-[60px] rounded-[4px] flex items-center justify-center'
                            style={{ backgroundColor: '#F4F3FF' }}
                        >
                            <img src="/image-markup.svg" className='w-full h-full object-cover' alt='image-markup' />
                        </div>
                        <h3 className="text-xl font-normal text-[#191919] py-2.5">Image Generation Settings</h3>
                        <p className=" text-sm  text-gray-500">
                            Choosing where images come from
                        </p>
                    </div>

                    <div className="flex min-w-0 flex-1 flex-col items-stretch justify-end gap-4 sm:items-end">
                        <div className="flex w-full min-w-0 flex-wrap gap-4 sm:justify-end items-start">
                            {!isImageGenerationDisabled && (
                                <>
                                    <div className="relative shrink-0 w-[222px]">
                                        <div className="flex flex-col justify-start ">
                                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                                Select Image Provider
                                            </label>
                                            <Popover
                                                open={openImageProviderSelect}
                                                onOpenChange={setOpenImageProviderSelect}
                                            >
                                                <PopoverTrigger asChild>
                                                    <Button
                                                        variant="outline"
                                                        role="combobox"
                                                        aria-expanded={openImageProviderSelect}
                                                        className="w-[222px] h-12 px-4 py-4 outline-none border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-colors hover:border-gray-400 justify-between"
                                                    >
                                                        <div className="flex gap-3 items-center">
                                                            <span className="text-sm font-medium text-gray-900">
                                                                {llmConfig.IMAGE_PROVIDER
                                                                    ? IMAGE_PROVIDERS[llmConfig.IMAGE_PROVIDER]
                                                                        ?.label || llmConfig.IMAGE_PROVIDER
                                                                    : "Select image provider"}
                                                            </span>
                                                        </div>
                                                        <ChevronUp className="w-4 h-4 text-gray-500" />
                                                    </Button>
                                                </PopoverTrigger>
                                                <PopoverContent
                                                    className="p-0"
                                                    align="start"
                                                    style={{ width: "300px" }}
                                                >
                                                    <Command>
                                                        <CommandInput placeholder="Search provider..." />
                                                        <CommandList>
                                                            <CommandEmpty>No provider found.</CommandEmpty>
                                                            <CommandGroup>
                                                                {Object.values(IMAGE_PROVIDERS).map(
                                                                    (provider, index) => (
                                                                        <CommandItem
                                                                            key={index}
                                                                            value={provider.value}
                                                                            onSelect={(value) => {
                                                                                input_field_changed(value, "IMAGE_PROVIDER");
                                                                                setOpenImageProviderSelect(false);
                                                                            }}
                                                                        >
                                                                            <Check
                                                                                className={cn(
                                                                                    "mr-2 h-4 w-4",
                                                                                    llmConfig.IMAGE_PROVIDER === provider.value
                                                                                        ? "opacity-100"
                                                                                        : "opacity-0"
                                                                                )}
                                                                            />
                                                                            <div className="flex gap-3 items-center">
                                                                                <div className="flex flex-col space-y-1 flex-1">
                                                                                    <div className="flex items-center justify-between gap-2">
                                                                                        <span className="text-sm font-medium text-gray-900 capitalize">
                                                                                            {provider.label}
                                                                                        </span>
                                                                                    </div>
                                                                                    <span className="text-xs text-gray-600 leading-relaxed">
                                                                                        {provider.description}
                                                                                    </span>
                                                                                </div>
                                                                            </div>
                                                                        </CommandItem>
                                                                    )
                                                                )}
                                                            </CommandGroup>
                                                        </CommandList>
                                                    </Command>
                                                </PopoverContent>
                                            </Popover>
                                        </div>
                                    </div>

                                    {llmConfig.IMAGE_PROVIDER &&
                                        IMAGE_PROVIDERS[llmConfig.IMAGE_PROVIDER] &&
                                        (() => {
                                            const provider = IMAGE_PROVIDERS[llmConfig.IMAGE_PROVIDER];

                                            if (provider.value === "openai_compatible") {
                                                return (
                                                    <OpenAICompatibleImageFields
                                                        layout="textProviderSettings"
                                                        baseUrl={llmConfig.OPENAI_COMPAT_IMAGE_BASE_URL || ""}
                                                        apiKey={llmConfig.OPENAI_COMPAT_IMAGE_API_KEY || ""}
                                                        model={llmConfig.OPENAI_COMPAT_IMAGE_MODEL || ""}
                                                        onBaseUrlChange={(v) => {
                                                            setLlmConfig((prev: any) => ({ ...prev, OPENAI_COMPAT_IMAGE_BASE_URL: v }));
                                                        }}
                                                        onApiKeyChange={(v) => {
                                                            setLlmConfig((prev: any) => ({ ...prev, OPENAI_COMPAT_IMAGE_API_KEY: v }));
                                                        }}
                                                        onModelChange={(v) => {
                                                            setLlmConfig((prev: any) => ({ ...prev, OPENAI_COMPAT_IMAGE_MODEL: v }));
                                                        }}
                                                        onModelListMetaChange={setOpenaiCompatListMeta}
                                                    />
                                                );
                                            }

                                            if (provider.value === "comfyui") {
                                                return (
                                                    <div className=" space-y-4">
                                                        <div className='w-[222px]'>
                                                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                                                ComfyUI Server URL
                                                            </label>
                                                            <div className="relative">
                                                                <input
                                                                    type="text"
                                                                    placeholder="http://192.168.1.7:8188"
                                                                    className="w-full px-2 py-3 outline-none border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-colors"
                                                                    value={llmConfig.COMFYUI_URL || ""}
                                                                    onChange={(e) => {
                                                                        input_field_changed(
                                                                            e.target.value,
                                                                            "COMFYUI_URL"
                                                                        );
                                                                    }}
                                                                />
                                                            </div>

                                                        </div>

                                                    </div>
                                                );
                                            }

                                            if (provider.value === "open_webui") {
                                                return (
                                                    <div className="space-y-4">
                                                        <div className='w-[222px]'>
                                                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                                                Open WebUI URL
                                                            </label>
                                                            <div className="relative">
                                                                <input
                                                                    type="text"
                                                                    placeholder="http://localhost:3000/api/v1"
                                                                    className="w-full px-2 py-3 outline-none border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-colors"
                                                                    value={llmConfig.OPEN_WEBUI_IMAGE_URL || ""}
                                                                    onChange={(e) => {
                                                                        input_field_changed(
                                                                            e.target.value,
                                                                            "OPEN_WEBUI_IMAGE_URL"
                                                                        );
                                                                    }}
                                                                />
                                                            </div>
                                                        </div>
                                                    </div>
                                                );
                                            }

                                            return (
                                                <div className=" w-[222px]">
                                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                                        {provider.apiKeyFieldLabel}
                                                    </label>
                                                    <div className="relative">
                                                        <input
                                                            type={showApiKey ? 'text' : 'password'}
                                                            placeholder={`Enter your ${provider.apiKeyFieldLabel}`}
                                                            className="w-full px-2 py-3 outline-none border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-colors"
                                                            value={getFieldValue(provider.apiKeyField)}
                                                            onChange={(e) =>
                                                                updateFieldValue(
                                                                    provider.apiKeyField,
                                                                    e.target.value
                                                                )
                                                            }
                                                        />
                                                        <button
                                                            type="button"
                                                            onClick={() => setShowApiKey((prev) => !prev)}
                                                            className='absolute right-2 top-1/2 -translate-y-1/2 bg-white px-2 py-1 cursor-pointer'
                                                        >
                                                            {showApiKey ? <Eye className='w-4 h-4 text-gray-500' /> : <EyeOff className='w-4 h-4 text-gray-500' />}
                                                        </button>
                                                    </div>

                                                </div>
                                            );
                                        })()}

                                </>
                            )}
                        </div>

                        {!isImageGenerationDisabled && (
                            <div className='flex flex-wrap justify-end items-start gap-4 w-full'>
                                {renderQualitySelector(llmConfig, input_field_changed)}
                                {llmConfig.IMAGE_PROVIDER === "open_webui" && (
                                    <div className='w-[222px]'>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            API Key (optional)
                                        </label>
                                        <div className="relative">
                                            <input
                                                type={showApiKey ? 'text' : 'password'}
                                                placeholder="API key"
                                                className="w-full px-2 py-3 outline-none border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-colors"
                                                value={llmConfig.OPEN_WEBUI_IMAGE_API_KEY || ""}
                                                onChange={(e) => {
                                                    input_field_changed(e.target.value, "OPEN_WEBUI_IMAGE_API_KEY");
                                                }}
                                            />
                                            <button
                                                type="button"
                                                onClick={() => setShowApiKey((prev) => !prev)}
                                                className='absolute right-2 top-1/2 -translate-y-1/2 bg-white px-2 py-1 cursor-pointer'
                                            >
                                                {showApiKey ? <Eye className='w-4 h-4 text-gray-500' /> : <EyeOff className='w-4 h-4 text-gray-500' />}
                                            </button>
                                        </div>
                                    </div>
                                )}
                                {llmConfig.IMAGE_PROVIDER === "comfyui" && (
                                    <div className='w-full min-w-[280px] max-w-full'>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            Workflow JSON
                                        </label>
                                        <div className="relative">
                                            <textarea
                                                placeholder='Paste your ComfyUI workflow JSON here (export via "Export (API)" in ComfyUI)'
                                                className="w-full px-4 py-2.5 outline-none border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-colors font-mono text-xs"
                                                rows={3}
                                                value={llmConfig.COMFYUI_WORKFLOW || ""}
                                                onChange={(e) => {
                                                    input_field_changed(
                                                        e.target.value,
                                                        "COMFYUI_WORKFLOW"
                                                    );
                                                }}
                                            />
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {!isImageGenerationDisabled &&
                llmConfig.IMAGE_PROVIDER === "openai_compatible" &&
                openaiCompatListMeta.modelsChecked &&
                openaiCompatListMeta.modelCount === 0 && (
                    <>
                        <div className="mb-4 rounded-lg border border-yellow-200 bg-yellow-50 p-3">
                            <p className="text-sm text-yellow-800">
                                No models found. Please make sure your provider credentials are valid and the selected provider is reachable.
                            </p>
                        </div>
                        <div className="flex w-full justify-end">
                            <div className="w-[222px]">
                                <label className="mb-2 block text-sm font-medium text-gray-700">Image model id</label>
                                <input
                                    type="text"
                                    placeholder="e.g. dall-e-3, gpt-image-1"
                                    className="w-full rounded-lg border border-gray-300 px-2 py-3 outline-none transition-colors focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
                                    value={llmConfig.OPENAI_COMPAT_IMAGE_MODEL || ""}
                                    onChange={(e) => {
                                        setLlmConfig((prev: any) => ({
                                            ...prev,
                                            OPENAI_COMPAT_IMAGE_MODEL: e.target.value,
                                        }));
                                    }}
                                />
                            </div>
                        </div>
                    </>
                )}
        </div>
    )
}

export default ImageProvider
