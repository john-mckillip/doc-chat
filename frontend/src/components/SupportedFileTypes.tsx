import React from 'react';

interface SupportedFileTypesProps {
    fileTypes?: string[];
    className?: string;
}

const defaultFileTypes = [
    '.md',
    '.txt',
    '.py',
    '.js',
    '.ts',
    '.tsx',
    '.cs',
    '.json'
];

export const SupportedFileTypes: React.FC<SupportedFileTypesProps> = ({
    fileTypes = defaultFileTypes,
    className = ''
}) => {
    return (
        <div className={`mt-6 p-4 bg-gray-50 rounded-lg ${className}`.trim()}>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">Supported File Types</h3>
            <div className="flex flex-wrap gap-2">
                {fileTypes.map((ext) => (
                    <span key={ext} className="text-xs bg-white px-2 py-1 rounded border border-gray-200 text-black">
                        {ext}
                    </span>
                ))}
            </div>
        </div>
    );
};
