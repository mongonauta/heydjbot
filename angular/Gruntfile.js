module.exports = function(grunt) {

    require('time-grunt')(grunt);
    require('jit-grunt')(grunt, {
        bower: 'grunt-bower-task'
    });

    grunt.initConfig({
        pkg: grunt.file.readJSON('package.json'),

        clean: {
            vendor: ['vendor', '../spotify/static/js/vendor.js', '../spotify/static/css/bootstrap.css'],
            build:  ['build'],
            dev: {
                src: ['../spotify/static/js/app.js', '../spotify/static/templates', '../spotify/static/css/style.css'],
            }
        },

        bower: {
            install: {
                // picks selected files from 'bower_components' folder and puts them into 'vendor'
                // the set of files that get copied is determined by the 'exportsOverride' config
                // in bower.json
                options: {
                    targetDir: './vendor',
                    layout: 'byType',
                    flatten: true
                }
            }
        },

        concat: {
            options: {
                separator: ';\n'
                // sourceMap: true,     // commenting out this line makes the build process much faster
            },
            vendor: {
                // first underscore.js, jquery.js and angular.js and then all other .js files
                src: [
                    'vendor/underscore/underscore.js',
                    'vendor/jquery/jquery.js',
                    'vendor/angular/angular.js',
                    'vendor/**/*.js'],
                dest: '../spotify/static/js/vendor.js'
            },
            dev: {
                src: [
                    'ng-src/js/app.js',            // first, main app file
                    'ng-src/js/**/index.js',       // then, main index.js file for each module
                    'ng-src/js/**/*.js'],          // and them the rest of .js files
                dest: '../spotify/static/js/app.js'
            }
        },

        ngAnnotate: {
            options: {
                // no options
            },
            prod: {
                files: {
                    '../spotify/static/js/app.js' : ['../spotify/static/js/app.js']
                }
            }
        },

        copy: {
            vendor: {
                // copy only css and fonts, because .js files are not copied, they are concat'ed
                files: [{
                    src: 'vendor/**/*.css',
                    dest: '../spotify/static/css/',
                    flatten: true,
                    expand: true
                },{
                    src: 'vendor/**/fontawesome*.*',
                    dest: '../spotify/static/fonts/',
                    flatten: true,
                    expand: true
                }]
            },
            dev: {
                // copy only css and html files, because .js files are not copied, they are concat'ed
                files: [{
                    src: ['ng-src/**/*.html', '!ng-src/index.html'],
                    dest: '../templates/',
                    flatten: true,
                    expand: true
                },{
                    src: ['ng-src/css/*.css','ng-src/css/**/*.css','ng-src/css/**/*.map'],
                    dest: '../spotify/static/css/',
                    flatten: true,
                    expand: true
                },{
                    src: [
                        'bower_components/bootstrap/dist/css/bootstrap.css',
                        'bower_components/bootstrap/dist/css/bootstrap.css.map'
                    ],
                    dest: '../spotify/static/css/',
                    flatten: true,
                    expand: true
                },{
                    src: 'ng-src/fonts/**/*.*',
                    dest: '../spotify/static/fonts/',
                    flatten: true,
                    expand: true
                }]
            },

            img: {
                files: [{
                    src: 'ng-src/img/**/*.*',
                    dest: '../spotify/static/img/',
                    flatten: true,
                    expand: true
                }]
            },

            fonts: {
                files: [{
                    src: 'ng-src/fonts/**/*.*',
                    dest: '../spotify/static/fonts/',
                    flatten: true,
                    expand: true
                }]
            },

        },

        // Javascript minification.
        uglify: {
            compile: {
                options: {
                    compress: true,
                    verbose: true
                },
                files: [{
                    src: '../spotify/static/js/vendor.js',
                    dest: '../spotify/static/js/vendor.min.js'
                }]
            }
        },

        jshint: {
            all: ['Gruntfile.js', 'ng-src/js/**/*.js'],
            dev: ['ng-src/js/**/*.js'],
            options: {                
                jshintrc: true
            },
            //test: ['client/spec/**/*.js']
        },

        less: {
            transpile: {
                options: {
                    compress: true,
                    sourceMap: true,
                    sourceMapURL: 'style.css.map',
                    outputSourceFiles: true
                },
                files: {
                    'ng-src/css/style.css': [
                        'ng-src/css/**/*.less'
                    ]
                }
            }
        },


        watch: {
            dev: {
                files: ['ng-src/**/*.html', 'ng-src/js/**/*.js'],//, 'ng-src/css/**/*.css'],
                tasks: ['build:code']
            },
            less: {
                files: ['ng-src/css/*.less'],
                tasks: ['less:transpile', 'copy:dev']
            },
        },

        concurrent: {
            options: {
                logConcurrentOutput: true,
                limit: 5
            },
            dev: {
                tasks: ['watch:dev',  'watch:less']
            },
        },

    });

    // run this task to install external dependencies in 'build' folder
    grunt.registerTask('init:dev', [
        'clean:vendor', 
        'bower', 
        'concat:vendor',
        'copy:vendor',
        'copy:img',
        'copy:fonts',
        'uglify',
        'less'
    ]);

    grunt.registerTask('build:code', [
        'clean:dev',
        'jshint:dev',
        'concat:dev',
        'ngAnnotate:prod',
        'copy:dev'
        // 'uglify',
    ]);

    // run this task to check *.js code using jshint and then 
    // concat and copy all required files (index.html, *.css, templates and app.js)
    // into 'build' folder
    grunt.registerTask('build:dev', [
        'less',
        'build:code'
    ]);

};
