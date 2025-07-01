const fs = require('fs');

module.exports = {
    runtimeCompiler: true,
    css: {
        extract: process.env.NODE_ENV === 'production', // 개발 모드에서는 CSS 추출 비활성화
        sourceMap: true
    },
    devServer: {
        port: 8081,
        allowedHosts: "all",
        https: true
    },
    configureWebpack: {
        optimization: {
            splitChunks: {
                chunks: 'all',
                maxSize: 244 * 1024, // 244 KiB
            },
        }
    }
}
