const fs = require('fs');

module.exports = {
    runtimeCompiler: true,
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
        },
    }
}
